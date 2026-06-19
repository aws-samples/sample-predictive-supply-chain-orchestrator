"""Defect tracking blueprint — defects list, summary, recall, report."""

import re
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
import structlog

logger = structlog.get_logger()

defects_bp = Blueprint("defects", __name__)


@defects_bp.route("/api/defects", methods=["GET"])
def get_defects():
    from api.state import csv_data_reader as data_reader

    try:
        defects = data_reader.get_defects()
        supplier_id = request.args.get("supplier_id")
        material_id = request.args.get("material_id")
        severity = request.args.get("severity")
        status = request.args.get("status")

        if severity and severity.upper() not in {"CRITICAL", "MAJOR", "MINOR"}:
            return jsonify({"error": "Invalid severity. Must be CRITICAL, MAJOR, or MINOR"}), 400
        if status and status.upper() not in {"OPEN", "RESOLVED", "CLOSED"}:
            return jsonify({"error": "Invalid status. Must be OPEN, RESOLVED, or CLOSED"}), 400

        if supplier_id:
            defects = [d for d in defects if d.supplier_id == supplier_id]
        if material_id:
            defects = [d for d in defects if d.material_id == material_id]
        if severity:
            defects = [d for d in defects if d.severity == severity.upper()]
        if status:
            defects = [d for d in defects if d.status == status.upper()]

        result = []
        for d in sorted(defects, key=lambda x: x.defect_date, reverse=True):
            supplier = data_reader.get_supplier_by_id(d.supplier_id)
            material = data_reader.get_material_by_id(d.material_id)
            result.append({
                **d.model_dump(mode="json"),
                "defect_date": d.defect_date.isoformat(),
                "resolution_date": d.resolution_date.isoformat() if d.resolution_date else None,
                "supplier_name": supplier.name if supplier else d.supplier_id,
                "material_name": material.name if material else d.material_id,
            })

        return jsonify({"defects": result, "total": len(result)}), 200
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("get_defects_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@defects_bp.route("/api/defects/summary", methods=["GET"])
def get_defect_summary():
    from api.state import csv_data_reader as data_reader

    try:
        defects = data_reader.get_defects()
        suppliers = data_reader.get_suppliers()
        materials = data_reader.get_materials()

        total = len(defects)
        open_count = sum(1 for d in defects if d.status == "OPEN")
        resolved_count = sum(1 for d in defects if d.status == "RESOLVED")
        recall_count = sum(1 for d in defects if d.recall_initiated)
        critical_count = sum(1 for d in defects if d.severity == "CRITICAL")
        total_affected = sum(d.quantity_affected for d in defects)

        by_severity = {}
        for sev in ["CRITICAL", "MAJOR", "MINOR"]:
            sev_defects = [d for d in defects if d.severity == sev]
            by_severity[sev] = {
                "count": len(sev_defects),
                "quantity_affected": sum(d.quantity_affected for d in sev_defects),
            }

        by_supplier = {}
        for s in suppliers:
            s_defects = [d for d in defects if d.supplier_id == s.supplier_id]
            if s_defects:
                by_supplier[s.supplier_id] = {
                    "supplier_name": s.name,
                    "total_defects": len(s_defects),
                    "open_defects": sum(1 for d in s_defects if d.status == "OPEN"),
                    "critical_defects": sum(1 for d in s_defects if d.severity == "CRITICAL"),
                    "recalls": sum(1 for d in s_defects if d.recall_initiated),
                    "quantity_affected": sum(d.quantity_affected for d in s_defects),
                    "defect_score": round(data_reader.get_supplier_defect_score(s.supplier_id), 2),
                }

        by_material = {}
        for m in materials:
            m_defects = [d for d in defects if d.material_id == m.material_id]
            if m_defects:
                by_material[m.material_id] = {
                    "material_name": m.name,
                    "total_defects": len(m_defects),
                    "critical_defects": sum(1 for d in m_defects if d.severity == "CRITICAL"),
                    "quantity_affected": sum(d.quantity_affected for d in m_defects),
                    "suppliers_affected": list(set(d.supplier_id for d in m_defects)),
                }

        categories = {}
        for d in defects:
            if d.category not in categories:
                categories[d.category] = 0
            categories[d.category] += 1

        return jsonify({
            "overview": {
                "total_defects": total,
                "open_defects": open_count,
                "resolved_defects": resolved_count,
                "recalls_initiated": recall_count,
                "critical_defects": critical_count,
                "total_units_affected": total_affected,
            },
            "by_severity": by_severity,
            "by_supplier": by_supplier,
            "by_material": by_material,
            "by_category": categories,
        }), 200
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("get_defect_summary_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@defects_bp.route("/api/defects/<defect_id>/recall", methods=["POST"])
def initiate_recall(defect_id: str):
    from api.state import csv_data_reader as data_reader

    try:
        if not re.match(r"^DEF-\d{3}$", defect_id):
            return jsonify({"error": "Invalid defect ID format. Expected DEF-NNN"}), 400

        defects = data_reader.get_defects()
        defect = next((d for d in defects if d.defect_id == defect_id), None)
        if not defect:
            return jsonify({"error": f"Defect {defect_id} not found"}), 404

        supplier = data_reader.get_supplier_by_id(defect.supplier_id)
        material = data_reader.get_material_by_id(defect.material_id)

        logger.info("recall_initiated", defect_id=defect_id,
                     supplier_id=defect.supplier_id, material_id=defect.material_id)

        return jsonify({
            "recall_id": f"RCL-{uuid.uuid4().hex[:8].upper()}",
            "defect_id": defect_id,
            "supplier_id": defect.supplier_id,
            "supplier_name": supplier.name if supplier else defect.supplier_id,
            "material_id": defect.material_id,
            "material_name": material.name if material else defect.material_id,
            "batch_id": defect.batch_id,
            "quantity_affected": defect.quantity_affected,
            "severity": defect.severity,
            "status": "RECALL_INITIATED",
            "initiated_at": datetime.utcnow().isoformat(),
            "message": f"Recall initiated for batch {defect.batch_id} — {defect.quantity_affected} units affected",
        }), 200
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("initiate_recall_failed", defect_id=defect_id, error=str(e))
        return jsonify({"error": str(e)}), 500


@defects_bp.route("/api/defects/report", methods=["GET"])
def get_defect_report():
    from api.state import csv_data_reader as data_reader

    try:
        supplier_id = request.args.get("supplier_id")
        defects = data_reader.get_defects()

        if supplier_id:
            defects = [d for d in defects if d.supplier_id == supplier_id]

        if not defects:
            return jsonify({"report": "No defects found for the given criteria.", "data": {}}), 200

        monthly = {}
        for d in defects:
            month_key = d.defect_date.strftime("%Y-%m")
            if month_key not in monthly:
                monthly[month_key] = {"total": 0, "critical": 0, "quantity": 0}
            monthly[month_key]["total"] += 1
            if d.severity == "CRITICAL":
                monthly[month_key]["critical"] += 1
            monthly[month_key]["quantity"] += d.quantity_affected

        resolution_times = []
        for d in defects:
            if d.resolution_date:
                days = (d.resolution_date - d.defect_date).days
                resolution_times.append(days)

        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None

        root_causes = {}
        for d in defects:
            cause = d.root_cause[:60]
            root_causes[cause] = root_causes.get(cause, 0) + 1
        top_causes = sorted(root_causes.items(), key=lambda x: x[1], reverse=True)[:5]

        return jsonify({
            "report": {
                "total_defects": len(defects),
                "avg_resolution_days": avg_resolution,
                "monthly_trend": dict(sorted(monthly.items())),
                "top_root_causes": [{"cause": c, "count": n} for c, n in top_causes],
                "recall_rate": round(sum(1 for d in defects if d.recall_initiated) / len(defects) * 100, 1),
                "open_rate": round(sum(1 for d in defects if d.status == "OPEN") / len(defects) * 100, 1),
            }
        }), 200
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("get_defect_report_failed", error=str(e))
        return jsonify({"error": str(e)}), 500
