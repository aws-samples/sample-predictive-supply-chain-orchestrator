"""
Flask API server for Procurement Optimization Agent.

Thin app factory — routes live in api/routes/ as Flask Blueprints.
Shared state (data_reader, neptune_client, etc.) lives in api/state.py.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
try:
    from flasgger import Swagger
except ImportError:
    Swagger = None  # type: ignore
try:
    from flask_talisman import Talisman
except ImportError:
    Talisman = None  # type: ignore
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    Limiter = None  # type: ignore
    get_remote_address = None  # type: ignore
import structlog

from config.settings import settings
from api import state
from api.routes import ALL_BLUEPRINTS

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Create Flask app
app = Flask(__name__)
CORS(app, origins=settings.cors_origins_list)

# Security headers
if Talisman is not None:
    Talisman(
        app,
        force_https=settings.flask_env == "production",
        content_security_policy={
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https:",
            "connect-src": "'self' https:",
        },
        content_security_policy_nonce_in=["script-src"],
        frame_options="DENY",
        strict_transport_security=settings.flask_env == "production",
    )

# Rate limiting
if Limiter is not None and get_remote_address is not None:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per minute", "50 per second"],
        storage_uri="memory://",
    )
else:
    limiter = None


@app.before_request
def _flush_pending_memory():
    if state.pending_memory_event is not None and not request.path.endswith("/chat"):
        evt = state.pending_memory_event
        state.pending_memory_event = None
        try:
            state._send_memory_event(*evt)
        except (ConnectionError, OSError):
            pass


# Swagger/OpenAPI
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Procurement Optimization Agent API",
        "description": "Multi-objective optimization API for supplier selection using Pareto frontier algorithm",
        "version": "1.0.0",
        "contact": {
            "name": "AWS CDE Team",
            "email": "cde@example.com"
        }
    },
    "host": f"localhost:{settings.flask_port}",
    "basePath": "/",
    "schemes": ["http"],
    "tags": [
        {"name": "Health", "description": "Health check endpoints"},
        {"name": "Data", "description": "Data access endpoints"},
        {"name": "Optimization", "description": "Supplier optimization endpoints"},
        {"name": "Purchase Requisitions", "description": "PR management endpoints"},
        {"name": "Defects", "description": "Defect tracking endpoints"},
        {"name": "Forecasting", "description": "Demand forecasting endpoints"},
        {"name": "Graph", "description": "Neptune graph endpoints"},
        {"name": "Risk", "description": "Risk simulation endpoints"},
        {"name": "Chat", "description": "Agent chat endpoints"},
        {"name": "Admin", "description": "Admin & observability endpoints"},
    ]
}

if Swagger is not None:
    swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Register all blueprints
for bp in ALL_BLUEPRINTS:
    app.register_blueprint(bp)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    logger.warning("endpoint_not_found", path=request.path)
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error("internal_server_error", error=str(error))
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info(
        "starting_server",
        port=settings.flask_port,
        environment=settings.flask_env,
        cors_origins=settings.cors_origins_list
    )
    app.run(
        host="127.0.0.1",  # nosec B104 — local dev only, Lambda uses Mangum
        port=settings.flask_port,
        debug=settings.flask_debug
    )
