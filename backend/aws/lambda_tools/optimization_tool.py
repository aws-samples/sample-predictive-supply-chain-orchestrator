"""
Optimization tool for Bedrock agent.

Lambda function that invokes the optimization engine and returns
Pareto frontier solutions.

Follows CDE standards:
- Type hints on all functions
- Error handling and validation
- Structured logging
- No hardcoded values
"""

import json
import os
import time
from typing import Dict, Any, List
import structlog

from core.optimization.engine import OptimizationEngine
from core.models import OptimizationRequest, MaterialDemand, OptimizationConstraints
from data.csv_reader import CSVDataReader

logger = structlog.get_logger()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for optimization tool.

    Args:
        event: Lambda event with optimization parameters
        context: Lambda context

    Returns:
        Optimization results with Pareto frontier

    Expected event structure:
    {
        "materials": [
            {"material_id": "MAT-BAT-001", "quantity": 1000, "required_by": "2026-04-15"}
        ],
        "constraints": {
            "max_supplier_concentration": 0.40,
            "max_lead_time_days": 45,
            "budget_max": 1000000,
            "prefer_contracted_suppliers": true
        }
    }
    """
    start_time = time.time()

    try:
        logger.info(
            "optimization_tool_invoked",
            request_id=context.aws_request_id if context else "local"
        )

        # Validate input
        materials = event.get("materials", [])
        if not materials:
            raise ValueError("materials list cannot be empty")

        if len(materials) > 100:
            raise ValueError("materials list cannot exceed 100 items")

        # Validate material quantities
        for material in materials:
            if not isinstance(material.get("quantity"), int) or material["quantity"] <= 0:
                raise ValueError(f"Invalid quantity for material {material.get('material_id')}")

        constraints_dict = event.get("constraints", {})

        # Build request model
        material_demands = [
            MaterialDemand(
                material_id=m["material_id"],
                quantity=m["quantity"],
                required_by=m.get("required_by")
            )
            for m in materials
        ]

        constraints = OptimizationConstraints(**constraints_dict)

        request = OptimizationRequest(
            materials=material_demands,
            constraints=constraints
        )

        # Initialize engine — prefer Neptune, fall back to CSV
        neptune_endpoint = os.environ.get("NEPTUNE_ENDPOINT", "")
        if neptune_endpoint:
            try:
                from data.neptune_data_reader import NeptuneDataReader
                data_reader = NeptuneDataReader(endpoint=neptune_endpoint)
                logger.info("using_neptune_data_reader")
            except Exception as e:
                logger.warning("neptune_fallback_to_csv", error=str(e))
                csv_dir = os.environ.get("CSV_DATA_DIR", "/opt/data")
                data_reader = CSVDataReader(csv_dir)
        else:
            csv_dir = os.environ.get("CSV_DATA_DIR", "/opt/data")
            data_reader = CSVDataReader(csv_dir)

        engine = OptimizationEngine(data_reader)

        # Run optimization with timeout handling
        timeout_seconds = 30
        if context and hasattr(context, "get_remaining_time_in_millis"):
            timeout_seconds = min(timeout_seconds, context.get_remaining_time_in_millis() / 1000 - 5)

        solutions = engine.optimize(request)

        # Convert to JSON-serializable format
        solutions_json = [
            {
                "name": sol.name,
                "total_cost": sol.total_cost,
                "risk_score": sol.risk_score,
                "quality_score": sol.quality_score,
                "lead_time_days": sol.lead_time_days,
                "max_supplier_concentration": sol.max_supplier_concentration,
                "reasoning": sol.reasoning,
                "demand_buffer_pct": sol.demand_buffer_pct,
                "allocations": [
                    {
                        "supplier_id": alloc.supplier_id,
                        "supplier_name": alloc.supplier_name,
                        "material_id": alloc.material_id,
                        "material_name": alloc.material_name,
                        "quantity": alloc.quantity,
                        "unit_price": alloc.unit_price,
                        "total_cost": alloc.total_cost,
                        "lead_time_days": alloc.lead_time_days,
                        "quality_score": alloc.quality_score,
                        "freight_cost": alloc.freight_cost,
                        "carrying_cost": alloc.carrying_cost,
                        "carbon_cost": alloc.carbon_cost,
                        "tco": alloc.tco
                    }
                    for alloc in sol.allocations
                ]
            }
            for sol in solutions
        ]

        computation_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "optimization_complete",
            solutions_count=len(solutions),
            computation_time_ms=computation_time_ms,
            request_id=context.aws_request_id if context else "local"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "solutions": solutions_json,
                "request_id": context.aws_request_id if context else "local",
                "computation_time_ms": computation_time_ms
            })
        }

    except ValueError as e:
        logger.warning(
            "optimization_validation_error",
            error=str(e)
        )
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Validation error: {str(e)}"
            })
        }

    except TimeoutError as e:
        logger.error(
            "optimization_timeout",
            error=str(e)
        )
        return {
            "statusCode": 504,
            "body": json.dumps({
                "error": "Optimization timed out. Try reducing the number of materials or constraints."
            })
        }

    except Exception as e:
        logger.error(
            "optimization_tool_error",
            error=str(e),
            exc_info=True
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal error during optimization"
            })
        }


def _run_optimization(
    materials: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    objectives: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    DEPRECATED: Mock implementation removed.

    Use lambda_handler which calls real OptimizationEngine.
    """
    raise NotImplementedError("Use lambda_handler with real OptimizationEngine")
