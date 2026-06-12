import os
from datetime import datetime
from flask import Blueprint, jsonify, request
import structlog
from api import state

logger = structlog.get_logger()
chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "Missing required field: message"}), 400
        logger.info("chat_request", message_length=len(message), agent_mode=os.environ.get("AGENT_MODE", "local"))
        if state.invoke_agent is not None:
            session_id = request.headers.get("X-Session-Id", data.get("session_id"))
            raw_user = request.headers.get("X-User-Id", data.get("user_id", "demo-user"))
            actor_id = raw_user.replace("@", "-at-").replace(".", "-")
            response_text = state.invoke_agent(message, session_id=session_id, actor_id=actor_id)
            agent_mode = os.environ.get("AGENT_MODE", "local")
            source = "agentcore" if agent_mode == "agentcore" else "strands-agent"
        else:
            response_text = "Agent not available. Please check backend configuration. Try asking about: optimize, explain, suppliers, risk, compare."
            source = "unavailable"
            session_id = None
            actor_id = "demo-user"
        logger.info("chat_response", response_length=len(response_text), source=source)
        state.pending_memory_event = (message, response_text, session_id, actor_id)
        return jsonify({"response": response_text, "source": source, "timestamp": datetime.now().isoformat()}), 200
    except (ValueError, TypeError, RuntimeError, ConnectionError) as e:
        logger.error("chat_failed", error=str(e))
        return jsonify({"error": str(e)}), 500
