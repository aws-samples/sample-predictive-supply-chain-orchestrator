from flask import Blueprint, jsonify, request
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

data_bp = Blueprint("data", __name__)


def _get_shared():
    from api.state import data_reader, neptune_client
    return data_reader, neptune_client


@data_bp.route("/api/suppliers", methods=["GET"])
def get_suppliers() -> tuple[Dict[str, Any], int]:
    data_reader, neptune_client = _get_shared()
    try:
        if neptune_client:
            suppliers_dict = neptune_client.get_suppliers()
            logger.info("suppliers_from_neptune", count=len(suppliers_dict))
        else:
            suppliers = data_reader.get_suppliers()
            suppliers_dict = [s.model_dump() for s in suppliers]
        return jsonify({"suppliers": suppliers_dict, "source": "neptune" if neptune_client else "csv"}), 200
    except (ConnectionError, OSError, ValueError) as e:
        logger.error("get_suppliers_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@data_bp.route("/api/materials", methods=["GET"])
def get_materials() -> tuple[Dict[str, Any], int]:
    data_reader, neptune_client = _get_shared()
    try:
        if neptune_client:
            materials_dict = neptune_client.get_materials()
        else:
            materials = data_reader.get_materials()
            materials_dict = [m.model_dump() for m in materials]
        return jsonify({"materials": materials_dict, "source": "neptune" if neptune_client else "csv"}), 200
    except (ConnectionError, OSError, ValueError) as e:
        logger.error("get_materials_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@data_bp.route("/api/supplier-materials", methods=["GET"])
def get_supplier_materials() -> tuple[Dict[str, Any], int]:
    data_reader, _ = _get_shared()
    try:
        supplier_materials = data_reader.get_supplier_materials()
        supplier_id = request.args.get('supplier_id')
        material_id = request.args.get('material_id')
        if supplier_id:
            supplier_materials = [sm for sm in supplier_materials if sm.supplier_id == supplier_id]
        if material_id:
            supplier_materials = [sm for sm in supplier_materials if sm.material_id == material_id]
        supplier_materials_dict = [sm.model_dump() for sm in supplier_materials]
        return jsonify({"supplier_materials": supplier_materials_dict}), 200
    except (ConnectionError, OSError, ValueError) as e:
        logger.error("get_supplier_materials_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@data_bp.route("/api/volume-tiers", methods=["GET"])
def get_volume_tiers() -> tuple[Dict[str, Any], int]:
    data_reader, _ = _get_shared()
    try:
        volume_tiers = data_reader.get_volume_tiers()
        supplier_material_id = request.args.get('supplier_material_id')
        if supplier_material_id:
            volume_tiers = [vt for vt in volume_tiers if vt.supplier_material_id == supplier_material_id]
        volume_tiers_dict = [vt.model_dump() for vt in volume_tiers]
        return jsonify({"volume_tiers": volume_tiers_dict}), 200
    except (ConnectionError, OSError, ValueError) as e:
        logger.error("get_volume_tiers_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@data_bp.route("/api/supplier-performance", methods=["GET"])
def get_supplier_performance() -> tuple[Dict[str, Any], int]:
    data_reader, _ = _get_shared()
    try:
        performance = data_reader.get_supplier_performance()
        supplier_id = request.args.get('supplier_id')
        if supplier_id:
            performance = [p for p in performance if p.supplier_id == supplier_id]
        performance_dict = [p.model_dump() for p in performance]
        return jsonify({"performance": performance_dict}), 200
    except (ConnectionError, OSError, ValueError) as e:
        logger.error("get_supplier_performance_failed", error=str(e))
        return jsonify({"error": str(e)}), 500
