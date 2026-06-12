from api.routes.health import health_bp
from api.routes.data import data_bp
from api.routes.optimization import optimization_bp
from api.routes.purchase_orders import purchase_orders_bp
from api.routes.defects import defects_bp
from api.routes.forecasting import forecasting_bp
from api.routes.graph import graph_bp
from api.routes.risk import risk_bp
from api.routes.chat import chat_bp
from api.routes.admin import admin_bp
from api.routes.evaluations import evaluations_bp

ALL_BLUEPRINTS = [
    health_bp,
    data_bp,
    optimization_bp,
    purchase_orders_bp,
    defects_bp,
    forecasting_bp,
    graph_bp,
    risk_bp,
    chat_bp,
    admin_bp,
    evaluations_bp,
]
