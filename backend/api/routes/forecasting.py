import json
import os
from flask import Blueprint, jsonify, request
from typing import Dict, Any
import structlog

import boto3
import pandas as pd

from api.state import (
    _get_forecast_s3_loader,
    _get_forecast_chronos_client,
    _prepare_material_timeseries,
    _build_agentcore_arn,
)

logger = structlog.get_logger()

forecasting_bp = Blueprint("forecasting", __name__)


@forecasting_bp.route("/api/forecast", methods=["POST"])
def proxy_forecast() -> tuple[Dict[str, Any], int]:
    """
    Proxy forecast request — routes to AgentCore (production) or local server (dev).

    In production (AGENT_MODE=agentcore + FORECAST_AGENT_ID set):
      Invokes the forecast agent on AgentCore Runtime with direct forecast mode.
    In local dev:
      Forwards to the local demand-forecasting server on port 8888.
    """
    try:
        data = request.get_json()
        if not data or not data.get("material_id"):
            return jsonify({"error": "Missing material_id", "status": "error"}), 400

        # Build forecast payload
        payload = {
            "action": "forecast",
            "material_id": data["material_id"],
            "prediction_length": min(data.get("prediction_length", 30), 90),
        }
        if data.get("product_id"):
            payload["product_id"] = data["product_id"]

        agent_mode = os.environ.get("AGENT_MODE", "local")
        forecast_agent_id = os.environ.get("FORECAST_AGENT_ID", "")

        # Production: invoke AgentCore forecast agent
        if agent_mode == "agentcore" and forecast_agent_id:
            logger.info("forecast_via_agentcore", agent_id=forecast_agent_id)
            agentcore_client = boto3.client(
                "bedrock-agentcore",
                region_name=os.environ.get("AWS_REGION", "us-east-1"),
            )
            resp = agentcore_client.invoke_agent_runtime(
                agentRuntimeArn=_build_agentcore_arn(forecast_agent_id),
                payload=json.dumps(payload),
            )

            # Parse AgentCore response — StreamingBody under "response" or "body" key
            raw = None
            for rkey in ("response", "body"):
                stream = resp.get(rkey)
                if stream and hasattr(stream, "read"):
                    raw = stream.read()
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    break
            if raw is None:
                raw = resp.get("response", resp.get("output", str(resp)))

            result = json.loads(raw) if isinstance(raw, str) else raw
            # Agent may return json.dumps(dict) — double-encoded string
            if isinstance(result, str):
                result = json.loads(result)
            logger.info("forecast_agentcore_success", material_id=data["material_id"])
            return jsonify(result), 200

        # Local dev: forward to demand-forecasting server
        import urllib.request
        local_url = os.environ.get("FORECAST_LOCAL_URL", "http://localhost:8888")
        req = urllib.request.Request(
            f"{local_url}/api/forecast",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        if not (local_url.startswith("http://") or local_url.startswith("https://")):
            raise ValueError(f"Refusing to open non-HTTP(S) URL: {local_url}")
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 — trusted local dev URL # nosemgrep: dynamic-urllib-use-detected
            result = json.loads(resp.read().decode("utf-8"))
        logger.info("forecast_local_proxy_success", material_id=data["material_id"])
        return jsonify(result), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON response from forecast agent", "status": "error"}), 502
    except (ConnectionError, OSError, TimeoutError) as e:
        logger.error("forecast_proxy_failed", error=str(e))
        return jsonify({"error": str(e), "status": "error"}), 503


@forecasting_bp.route("/api/demand/forecast", methods=["POST"])
def demand_forecast() -> tuple[Dict[str, Any], int]:
    """
    Direct demand forecast — calls SageMaker Chronos-2 directly (no AgentCore).
    This is the fast path used by the UI "Run Forecast" button.
    """
    try:
        data = request.get_json()
        if not data or not data.get("material_id"):
            return jsonify({"error": "Missing material_id", "status": "error"}), 400

        material_id = data["material_id"]
        prediction_length = min(data.get("prediction_length", 30), 90)
        product_id = data.get("product_id", None)

        # Direct SageMaker Chronos-2 path
        context_df = _prepare_material_timeseries(material_id, product_id=product_id)
        if context_df.empty:
            return jsonify({"error": f"No historical data for {material_id}", "status": "error"}), 404

        # Call SageMaker Chronos-2
        chronos = _get_forecast_chronos_client()
        if not chronos:
            return jsonify({"error": "Chronos endpoint not configured", "status": "error"}), 503

        time_series = context_df["target"].tolist()
        chronos_result = chronos.forecast(time_series=time_series, prediction_length=prediction_length)

        # Build forecast points
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

        # Explainability stats
        ts = context_df["target"]
        hist_mean = float(ts.mean())
        hist_std = float(ts.std()) if len(ts) > 1 else 0
        cv = round(hist_std / hist_mean, 2) if hist_mean > 0 else 0
        half = len(ts) // 2
        first_half_avg = float(ts.iloc[:half].mean()) if half > 0 else hist_mean
        second_half_avg = float(ts.iloc[half:].mean()) if half > 0 else hist_mean
        trend_pct = round((second_half_avg - first_half_avg) / first_half_avg * 100, 1) if first_half_avg > 0 else 0
        trend_direction = "increasing" if trend_pct > 5 else ("decreasing" if trend_pct < -5 else "stable")
        context_copy = context_df.copy()
        context_copy["dow"] = context_copy["timestamp"].dt.dayofweek
        dow_avg = context_copy.groupby("dow")["target"].mean()
        seasonal_strength = round(float(dow_avg.std()) / hist_mean, 2) if hist_mean > 0 else 0
        recent_window = min(30, len(ts))
        recent_avg = float(ts.iloc[-recent_window:].mean())
        momentum_pct = round((recent_avg - hist_mean) / hist_mean * 100, 1) if hist_mean > 0 else 0
        spread_ratio = round((total_p90 - total_p10) / total_p50 * 100, 1) if total_p50 > 0 else 0

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
            "explainability": {
                "hist_mean": round(hist_mean, 2),
                "hist_std": round(hist_std, 2),
                "hist_min": int(ts.min()),
                "hist_max": int(ts.max()),
                "cv": cv,
                "trend_direction": trend_direction,
                "trend_pct": trend_pct,
                "seasonal_strength": seasonal_strength,
                "recent_avg": round(recent_avg, 2),
                "momentum_pct": momentum_pct,
                "spread_ratio": spread_ratio,
                "data_span_days": len(ts),
            },
            "forecast": forecast_points,
            "model": "chronos-2",
            "status": "success",
        }

        logger.info("demand_forecast_success", material_id=material_id, prediction_length=prediction_length)
        return jsonify(result), 200

    except (ConnectionError, OSError, ValueError) as e:
        logger.error("demand_forecast_failed", error=str(e))
        return jsonify({"error": str(e), "status": "error"}), 500
