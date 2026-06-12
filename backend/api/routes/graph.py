from flask import Blueprint, jsonify
import structlog

logger = structlog.get_logger()

graph_bp = Blueprint("graph", __name__)


@graph_bp.route("/api/graph/network", methods=["GET"])
def get_network():
    from api.state import neptune_client

    try:
        if neptune_client:
            network = neptune_client.get_supply_network()
            logger.info("graph_network", source="neptune")
            return jsonify({"network": network, "source": "neptune"}), 200
        else:
            logger.warning("graph_network_unavailable")
            return jsonify({"network": {}, "message": "Neptune not connected"}), 200
    except (ConnectionError, OSError, RuntimeError) as e:
        logger.error("get_network_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/api/graph/alternatives/<material_id>", methods=["GET"])
def get_alternatives(material_id):
    from api.state import neptune_client

    try:
        if neptune_client:
            alternatives = neptune_client.find_alternative_suppliers(material_id)
            logger.info("graph_alternatives", material_id=material_id, count=len(alternatives))
            return jsonify({"alternatives": alternatives, "material_id": material_id}), 200
        else:
            logger.warning("graph_alternatives_unavailable", material_id=material_id)
            return jsonify({"alternatives": [], "material_id": material_id, "message": "Neptune not connected"}), 200
    except (ConnectionError, OSError, RuntimeError) as e:
        logger.error("get_alternatives_failed", material_id=material_id, error=str(e))
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/api/graph/supplier-materials/<supplier_id>", methods=["GET"])
def get_supplier_materials(supplier_id):
    from api.state import neptune_client

    try:
        if neptune_client:
            materials = neptune_client.get_supplier_materials(supplier_id)
            logger.info("graph_supplier_materials", supplier_id=supplier_id, count=len(materials))
            return jsonify({"materials": materials, "supplier_id": supplier_id}), 200
        else:
            logger.warning("graph_supplier_materials_unavailable", supplier_id=supplier_id)
            return jsonify({"materials": [], "supplier_id": supplier_id, "message": "Neptune not connected"}), 200
    except (ConnectionError, OSError, RuntimeError) as e:
        logger.error("get_supplier_materials_failed", supplier_id=supplier_id, error=str(e))
        return jsonify({"error": str(e)}), 500
