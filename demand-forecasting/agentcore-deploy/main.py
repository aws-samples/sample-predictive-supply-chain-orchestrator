"""
AgentCore Runtime entrypoint for demand forecasting agent.

Uses BedrockAgentCoreApp to expose the Strands forecasting agent
via AgentCore Runtime. Supports two modes:
  1. LLM-powered queries via prompt (seasonal analysis agent)
  2. Direct forecast via action (mock Chronos, no LLM)
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agents.seasonal_analysis_agent import (
    load_bike_sales_data,
    load_maintenance_data,
    explode_sales_to_materials,
    analyze_seasonal_patterns,
    get_material_info,
)
from agents.chronos_forecasting_agent import (
    prepare_material_timeseries,
    generate_mock_forecast,
    get_chronos_pipeline,
    CHRONOS_AVAILABLE,
)

app = BedrockAgentCoreApp()

# Wrap tools for Strands
sales_tool = tool(load_bike_sales_data)
maintenance_tool = tool(load_maintenance_data)
explode_tool = tool(explode_sales_to_materials)
seasonal_tool = tool(analyze_seasonal_patterns)
material_tool = tool(get_material_info)

# Create agent with Bedrock model
model_id = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
model = BedrockModel(model_id=model_id)

agent = Agent(
    model=model,
    tools=[sales_tool, maintenance_tool, explode_tool, seasonal_tool, material_tool],
    system_prompt="""You are a Demand Forecasting Agent for VoltCycle e-bike manufacturing.
Analyze historical sales and maintenance data to identify seasonal patterns and forecast demand.
Keep ALL responses under 3 sentences. Be extremely concise. Only state the most important insight.""",
)


def handle_direct_forecast(material_id: str, prediction_length: int = 90):
    """Direct forecast without LLM — uses Chronos mock for fast response."""
    import pandas as pd

    context_df = prepare_material_timeseries(material_id)
    if context_df.empty:
        return json.dumps({"error": f"No historical data for {material_id}", "status": "error"})

    context_df["id"] = material_id
    quantile_levels = [0.1, 0.5, 0.9]

    pipeline = get_chronos_pipeline()
    if CHRONOS_AVAILABLE and pipeline is not None:
        pred_df = pipeline.predict_df(
            context_df, prediction_length=prediction_length,
            quantile_levels=quantile_levels, id_column="id",
            timestamp_column="timestamp", target="target",
        )
    else:
        pred_df = generate_mock_forecast(context_df, prediction_length, quantile_levels)

    forecast_points = []
    for _, row in pred_df.iterrows():
        forecast_points.append({
            "date": row["timestamp"].strftime("%Y-%m-%d"),
            "p10": round(float(row["0.1"]), 2),
            "p50": round(float(row["0.5"]), 2),
            "p90": round(float(row["0.9"]), 2),
        })

    total_p10 = sum(f["p10"] for f in forecast_points)
    total_p50 = sum(f["p50"] for f in forecast_points)
    total_p90 = sum(f["p90"] for f in forecast_points)

    return json.dumps({
        "material_id": material_id,
        "prediction_length": prediction_length,
        "summary": {
            "total_p10": round(total_p10, 1),
            "total_p50": round(total_p50, 1),
            "total_p90": round(total_p90, 1),
            "avg_daily_p50": round(total_p50 / prediction_length, 2),
        },
        "forecast": forecast_points,
        "model": "chronos-2" if CHRONOS_AVAILABLE else "mock",
        "status": "success",
    })


@app.entrypoint
def forecast_agent_handler(payload):
    """
    Invoke the forecasting agent.

    Payload options:
      {"prompt": "Analyze seasonal patterns for MAT-BAT-001"}  -> LLM agent
      {"action": "forecast", "material_id": "MAT-BAT-001", "prediction_length": 90}  -> direct
    """
    action = payload.get("action")

    if action == "forecast":
        material_id = payload.get("material_id", "")
        prediction_length = min(payload.get("prediction_length", 90), 90)
        if not material_id:
            return json.dumps({"error": "Missing material_id", "status": "error"})
        return handle_direct_forecast(material_id, prediction_length)

    # Default: LLM-powered query
    user_input = payload.get("prompt", "")
    print(f"User input: {user_input}")
    response = agent(user_input)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
