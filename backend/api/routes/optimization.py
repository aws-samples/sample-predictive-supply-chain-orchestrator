import time
import uuid
from flask import Blueprint, jsonify, request
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

optimization_bp = Blueprint("optimization", __name__)


@optimization_bp.route("/api/optimize", methods=["POST"])
def optimize_suppliers() -> tuple[Dict[str, Any], int]:
    from api.state import optimization_engine
    from core.models import OptimizationRequest, OptimizationResponse

    start_time = time.time()
    request_id = str(uuid.uuid4())
    try:
        if optimization_engine is None:
            logger.error("optimization_engine_not_available", request_id=request_id)
            return jsonify({"error": "Optimization engine not available"}), 503
        data = request.get_json()
        opt_request = OptimizationRequest(**data)
        logger.info(
            "optimization_request",
            request_id=request_id,
            materials_count=len(opt_request.materials),
            max_concentration=opt_request.constraints.max_supplier_concentration
        )
        solutions = optimization_engine.optimize(opt_request)
        computation_time_ms = int((time.time() - start_time) * 1000)
        response = OptimizationResponse(
            solutions=solutions,
            request_id=request_id,
            computation_time_ms=computation_time_ms
        )
        logger.info(
            "optimization_complete",
            request_id=request_id,
            solutions_count=len(solutions),
            computation_time_ms=computation_time_ms
        )
        return jsonify(response.model_dump()), 200
    except ValueError as e:
        logger.warning("optimization_validation_error", request_id=request_id, error=str(e))
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except (RuntimeError, TypeError, KeyError) as e:
        logger.error("optimization_failed", request_id=request_id, error=str(e), exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@optimization_bp.route("/api/optimize-custom", methods=["POST"])
def optimize_custom():
    from api.state import optimization_engine
    from core.models import MaterialDemand, OptimizationConstraints, OptimizationRequest

    try:
        data = request.get_json()
        weights = data.get("weights", {"cost": 0.4, "risk": 0.3, "lead_time": 0.3})
        materials = data.get("materials", [
            {"material_id": f"MAT-BAT-00{i}", "quantity": 500} for i in range(1, 4)
        ] + [
            {"material_id": f"MAT-MOT-00{i}", "quantity": 500} for i in [1, 3, 4]
        ] + [
            {"material_id": f"MAT-FRM-00{i}", "quantity": 500} for i in [1, 3, 4]
        ] + [
            {"material_id": f"MAT-ELC-00{i}", "quantity": 500} for i in range(1, 4)
        ] + [
            {"material_id": f"MAT-STD-00{i}", "quantity": 500} for i in range(1, 5)
        ])
        constraints = data.get("constraints", {
            "max_supplier_concentration": 0.60,
            "max_lead_time_days": 60,
            "budget_max": 5000000,
        })

        material_demands = [MaterialDemand(**m) for m in materials]
        opt_constraints = OptimizationConstraints(**constraints)
        opt_request = OptimizationRequest(materials=material_demands, constraints=opt_constraints)

        start = time.time()
        problem = optimization_engine._build_problem(opt_request)
        solution_arr = optimization_engine._solve_weighted_sum(problem, weights, opt_constraints)
        supplier_mix = optimization_engine._build_supplier_mix("Custom", solution_arr, problem, opt_request)
        elapsed_ms = int((time.time() - start) * 1000)

        sol = {
            "name": "Custom",
            "total_cost": supplier_mix.total_cost,
            "risk_score": supplier_mix.risk_score,
            "quality_score": supplier_mix.quality_score,
            "lead_time_days": supplier_mix.lead_time_days,
            "max_supplier_concentration": supplier_mix.max_supplier_concentration,
            "reasoning": supplier_mix.reasoning,
            "allocations": [
                {
                    "supplier_id": a.supplier_id,
                    "supplier_name": a.supplier_name,
                    "material_id": a.material_id,
                    "material_name": a.material_name,
                    "quantity": a.quantity,
                    "unit_price": a.unit_price,
                    "total_cost": a.total_cost,
                    "lead_time_days": a.lead_time_days,
                    "quality_score": a.quality_score,
                    "freight_cost": a.freight_cost,
                    "carrying_cost": a.carrying_cost,
                    "carbon_cost": a.carbon_cost,
                    "tco": a.tco,
                }
                for a in supplier_mix.allocations
            ],
        }
        return jsonify({"solution": sol, "weights": weights, "computation_time_ms": elapsed_ms}), 200
    except (ValueError, TypeError, RuntimeError, KeyError) as e:
        logger.error("optimize_custom_failed", error=str(e))
        return jsonify({"error": str(e)}), 500
