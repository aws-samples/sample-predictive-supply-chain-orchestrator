import os
from flask import Blueprint, jsonify
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check() -> tuple[Dict[str, Any], int]:
    from core.models import HealthCheckResponse
    from config.settings import settings
    try:
        agent_mode = os.environ.get("AGENT_MODE", "local")
        procurement_agent_id = os.environ.get("PROCUREMENT_AGENT_ID", os.environ.get("AGENTCORE_AGENT_ID", ""))
        forecast_agent_id = os.environ.get("FORECAST_AGENT_ID", "")
        response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            environment=settings.flask_env
        )
        result = response.model_dump()
        result["agent_mode"] = agent_mode
        result["procurement_agent"] = {
            "id": procurement_agent_id or "(not set)",
            "status": "configured" if procurement_agent_id else "local-only",
        }
        result["forecast_agent"] = {
            "id": forecast_agent_id or "(not set)",
            "status": "configured" if forecast_agent_id else "local-only",
        }
        result["sagemaker_endpoint"] = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "(not set)")
        logger.info("health_check", status="success", agent_mode=agent_mode)
        return jsonify(result), 200
    except (KeyError, ValueError, RuntimeError) as e:
        logger.error("health_check_failed", error=str(e))
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
