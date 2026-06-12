"""
AgentCore Runtime entrypoint for demand forecasting agent.

Uses BedrockAgentCoreApp to expose the forecasting agent via AgentCore Runtime.
Supports two invocation modes:
  - Direct forecast: {"action": "forecast", "material_id": "MAT-BAT-001", "prediction_length": 90}
  - LLM query: {"prompt": "forecast MAT-BAT-001 for 90 days"}
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

from data.s3_data_loader import S3DataLoader
from data.chronos_client import ChronosClient

app = BedrockAgentCoreApp()

# --- Configuration from environment ---
DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
FORECAST_DATA_PREFIX = os.environ.get("FORECAST_DATA_PREFIX", "forecast-data/")
SAGEMAKER_ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "chronos-2-forecast-endpoint")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

# --- Shared clients (initialized once per runtime) ---
s3_loader = S3DataLoader(bucket_name=DATA_BUCKET, prefix=FORECAST_DATA_PREFIX)
chronos_client = ChronosClient(endpoint_name=SAGEMAKER_ENDPOINT_NAME)


# ── Data helpers (same logic as local server.py) ────────────────────

def prepare_material_timeseries(
    material_id: str,
    product_id: str | None = None,
) -> pd.DataFrame:
    """
    Prepare time series data for a material by combining sales + maintenance demand.
    Same logic as the local chronos_forecasting_agent.prepare_material_timeseries(),
    but reads from S3 instead of local files.
    """
    sales_data = s3_loader.load_csv("bike_sales_history.csv")
    maint_data = s3_loader.load_csv("maintenance_demand_history.csv")
    bom_data = s3_loader.load_csv("bom.csv")

    # BOM lookup: product_id -> [(material_id, qty_required)]
    bom_lookup = defaultdict(list)
    for entry in bom_data:
        bom_lookup[entry["product_id"]].append({
            "material_id": entry["material_id"],
            "quantity_required": float(entry["quantity_required"]),
        })

    # Aggregate daily demand from sales (via BOM) + maintenance
    demand_by_date: dict[str, int] = defaultdict(int)

    for sale in sales_data:
        if product_id and product_id != "ALL" and sale["product_id"] != product_id:
            continue
        date = sale["timestamp"].split()[0]
        bikes_sold = int(sale["quantity_sold"])
        for bom_item in bom_lookup[sale["product_id"]]:
            if bom_item["material_id"] == material_id:
                demand_by_date[date] += int(bikes_sold * bom_item["quantity_required"])

    for maint in maint_data:
        if maint["material_id"] == material_id:
            date = maint["timestamp"].split()[0]
            demand_by_date[date] += int(maint["quantity"])

    if not demand_by_date:
        return pd.DataFrame(columns=["timestamp", "target"])

    df = pd.DataFrame([
        {"timestamp": d, "target": v} for d, v in sorted(demand_by_date.items())
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Fill missing dates with 0
    date_range = pd.date_range(start=df["timestamp"].min(), end=df["timestamp"].max(), freq="D")
    df = df.set_index("timestamp").reindex(date_range, fill_value=0).reset_index()
    df.columns = ["timestamp", "target"]
    return df


def build_explainability(context_df: pd.DataFrame, total_p10: float, total_p50: float, total_p90: float) -> dict:
    """Build explainability stats from historical data — same as server.py."""
    ts = context_df["target"]
    hist_mean = float(ts.mean())
    hist_std = float(ts.std()) if len(ts) > 1 else 0
    cv = round(hist_std / hist_mean, 2) if hist_mean > 0 else 0

    half = len(ts) // 2
    first_half_avg = float(ts.iloc[:half].mean()) if half > 0 else hist_mean
    second_half_avg = float(ts.iloc[half:].mean()) if half > 0 else hist_mean
    trend_pct = round((second_half_avg - first_half_avg) / first_half_avg * 100, 1) if first_half_avg > 0 else 0
    if trend_pct > 5:
        trend_direction = "increasing"
    elif trend_pct < -5:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    context_copy = context_df.copy()
    context_copy["dow"] = context_copy["timestamp"].dt.dayofweek
    dow_avg = context_copy.groupby("dow")["target"].mean()
    seasonal_strength = round(float(dow_avg.std()) / hist_mean, 2) if hist_mean > 0 else 0

    recent_window = min(30, len(ts))
    recent_avg = float(ts.iloc[-recent_window:].mean())
    momentum_pct = round((recent_avg - hist_mean) / hist_mean * 100, 1) if hist_mean > 0 else 0
    spread_ratio = round((total_p90 - total_p10) / total_p50 * 100, 1) if total_p50 > 0 else 0

    return {
        "hist_mean": round(hist_mean, 2),
        "hist_std": round(hist_std, 2),
        "hist_min": int(ts.min()),
        "hist_max": int(ts.max()),
        "cv": cv,
        "trend_direction": trend_direction,
        "trend_pct": trend_pct,
        "first_half_avg": round(first_half_avg, 2),
        "second_half_avg": round(second_half_avg, 2),
        "seasonal_strength": seasonal_strength,
        "dow_pattern": {int(k): round(v, 2) for k, v in dow_avg.to_dict().items()},
        "recent_avg": round(recent_avg, 2),
        "momentum_pct": momentum_pct,
        "spread_ratio": spread_ratio,
        "data_span_days": len(ts),
    }


def handle_direct_forecast(payload: dict) -> str:
    """
    Direct forecast path — bypasses LLM, calls SageMaker Chronos-2 directly.
    Same response format as the local server.py /api/forecast endpoint.
    """
    material_id = payload.get("material_id", "")
    prediction_length = min(payload.get("prediction_length", 30), 90)
    product_id = payload.get("product_id", None)

    if not material_id:
        return json.dumps({"error": "Missing material_id", "status": "error"})

    context_df = prepare_material_timeseries(material_id, product_id=product_id)
    if context_df.empty:
        return json.dumps({"error": f"No historical data for {material_id}", "status": "error"})

    # Invoke SageMaker Chronos-2 endpoint
    time_series = context_df["target"].tolist()
    chronos_result = chronos_client.forecast(
        time_series=time_series,
        prediction_length=prediction_length,
    )

    # Build forecast points from Chronos response
    from datetime import date as _date
    today = pd.Timestamp(_date.today())
    future_dates = pd.date_range(start=today, periods=prediction_length, freq="D")

    forecast_points = []
    for i, dt in enumerate(future_dates):
        forecast_points.append({
            "date": dt.strftime("%Y-%m-%d"),
            "p10": round(float(chronos_result["p10"][i]), 2) if i < len(chronos_result["p10"]) else 0,
            "p50": round(float(chronos_result["p50"][i]), 2) if i < len(chronos_result["p50"]) else 0,
            "p90": round(float(chronos_result["p90"][i]), 2) if i < len(chronos_result["p90"]) else 0,
        })

    total_p10 = sum(f["p10"] for f in forecast_points)
    total_p50 = sum(f["p50"] for f in forecast_points)
    total_p90 = sum(f["p90"] for f in forecast_points)

    explainability = build_explainability(context_df, total_p10, total_p50, total_p90)

    result = {
        "material_id": material_id,
        "prediction_length": prediction_length,
        "summary": {
            "total_p10": round(total_p10, 1),
            "total_p50": round(total_p50, 1),
            "total_p90": round(total_p90, 1),
            "avg_daily_p50": round(total_p50 / prediction_length, 2),
        },
        "historical": {
            "data_points": len(context_df),
            "total_demand": int(context_df["target"].sum()),
            "avg_daily": round(float(context_df["target"].mean()), 2),
        },
        "explainability": explainability,
        "forecast": forecast_points,
        "model": "chronos-2",
        "status": "success",
    }
    return json.dumps(result)


# ── Strands agent tools (for LLM path) ─────────────────────────────

@tool
def generate_forecast(material_id: str, prediction_length: int = 30) -> str:
    """Generate demand forecast for a material using Chronos-2 on SageMaker.

    Args:
        material_id: Material ID (e.g., MAT-BAT-001)
        prediction_length: Number of days to forecast (max 90)

    Returns:
        JSON string with forecast results
    """
    payload = {"action": "forecast", "material_id": material_id, "prediction_length": prediction_length}
    return handle_direct_forecast(payload)


@tool
def list_available_materials() -> str:
    """List all materials available for forecasting.

    Returns:
        JSON string with material IDs, names, and categories
    """
    materials_data = s3_loader.load_csv("materials.csv")
    result = {
        "total_materials": len(materials_data),
        "materials": [
            {"material_id": m["material_id"], "name": m["name"], "category": m["category"]}
            for m in materials_data
        ],
    }
    return json.dumps(result, indent=2)


@tool
def get_material_info(material_id: str) -> str:
    """Get detailed information about a specific material.

    Args:
        material_id: Material ID (e.g., MAT-BAT-001)

    Returns:
        JSON string with material details
    """
    materials_data = s3_loader.load_csv("materials.csv")
    material = next((m for m in materials_data if m["material_id"] == material_id), None)
    if not material:
        return json.dumps({"error": f"Material {material_id} not found", "status": "error"})
    return json.dumps(material, indent=2)


@tool
def analyze_seasonal_patterns(material_id: str) -> str:
    """Analyze seasonal demand patterns for a material.

    Args:
        material_id: Material ID (e.g., MAT-BAT-001)

    Returns:
        JSON string with seasonal analysis
    """
    context_df = prepare_material_timeseries(material_id)
    if context_df.empty:
        return json.dumps({"error": f"No data for {material_id}", "status": "error"})

    context_df["month"] = context_df["timestamp"].dt.month
    monthly = context_df.groupby("month")["target"].agg(["mean", "sum", "count"]).reset_index()

    seasons = {
        "WINTER": [12, 1, 2],
        "SPRING": [3, 4, 5],
        "SUMMER": [6, 7, 8],
        "FALL": [9, 10, 11],
    }
    seasonal_demand = {}
    for season, months in seasons.items():
        mask = context_df["month"].isin(months)
        seasonal_demand[season] = round(float(context_df.loc[mask, "target"].mean()), 2)

    return json.dumps({
        "material_id": material_id,
        "seasonal_demand": seasonal_demand,
        "monthly_avg": {int(r["month"]): round(float(r["mean"]), 2) for _, r in monthly.iterrows()},
        "data_points": len(context_df),
        "status": "success",
    }, indent=2)


# ── LLM agent (lazy init) ──────────────────────────────────────────

_agent = None


def _get_agent() -> Agent:
    """Lazy-initialize the Strands agent."""
    global _agent
    if _agent is None:
        model = BedrockModel(model_id=BEDROCK_MODEL_ID)
        _agent = Agent(
            model=model,
            tools=[generate_forecast, list_available_materials, get_material_info, analyze_seasonal_patterns],
            system_prompt=(
                "You are a demand forecasting agent for VoltCycle e-bike manufacturing. "
                "You can generate Chronos-2 forecasts, analyze seasonal patterns, and "
                "look up material information. Keep responses under 3 sentences. "
                "Be concise and state the most important insight."
            ),
        )
    return _agent


# ── AgentCore entrypoint ────────────────────────────────────────────

@app.entrypoint
def forecast_agent_handler(payload):
    """
    Dual-mode handler for the forecast agent.

    Direct mode: {"action": "forecast", "material_id": "...", "prediction_length": N}
    LLM mode:    {"prompt": "forecast MAT-BAT-001 for 90 days"}
    """
    # Direct forecast path — no LLM, fast
    if payload.get("action") == "forecast":
        return handle_direct_forecast(payload)

    # LLM query path — Strands agent with Bedrock Nova
    prompt = payload.get("prompt", "")
    if prompt:
        agent = _get_agent()
        response = agent(prompt)
        return response.message["content"][0]["text"]

    # Invalid payload
    return json.dumps({
        "error": "Invalid request. Use {\"action\": \"forecast\", \"material_id\": \"...\"} or {\"prompt\": \"...\"}",
        "status": "error",
    })


if __name__ == "__main__":
    app.run()
