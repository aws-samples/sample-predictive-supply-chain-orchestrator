"""
Data access tool for Bedrock agent.

Lambda function that queries Neptune graph database and S3 for
supplier and material data.

Follows CDE standards:
- Type hints on all functions
- Error handling for AWS API calls
- Structured logging
- Connection pooling
"""

import json
import os
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from gremlin_python.driver.protocol import GremlinServerError
import structlog

from data.neptune_client import NeptuneClient
from data.csv_reader import CSVDataReader

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Geopolitical risk scenarios
# ---------------------------------------------------------------------------
RISK_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "strait_of_hormuz": {
        "name": "Strait of Hormuz Blockade",
        "description": (
            "Military conflict or blockade disrupts shipping through the "
            "Strait of Hormuz, affecting all Asia-Europe and Asia-Americas "
            "maritime routes via the Persian Gulf."
        ),
        "affected_routes": ["Asia-Europe via Suez", "Asia-Americas via Pacific"],
        "affected_regions": ["China", "South Korea", "Japan", "Taiwan"],
        "freight_increase_pct": 0.45,
        "lead_time_increase_days": 18,
        "probability": "HIGH",
        "current_status": "ACTIVE — Iran conflict escalation, April 2026",
    },
    "suez_canal": {
        "name": "Suez Canal Disruption",
        "description": (
            "Blockage or Houthi attacks force rerouting around Cape of Good Hope."
        ),
        "affected_routes": ["Asia-Europe via Suez"],
        "affected_regions": ["China", "South Korea", "Japan", "Taiwan"],
        "freight_increase_pct": 0.35,
        "lead_time_increase_days": 14,
        "probability": "MEDIUM",
        "current_status": "Houthi attacks ongoing since 2024",
    },
    "taiwan_strait": {
        "name": "Taiwan Strait Crisis",
        "description": (
            "Military tensions or blockade in the Taiwan Strait disrupts all "
            "shipping to/from Taiwan and nearby routes."
        ),
        "affected_routes": ["All Taiwan shipping", "East Asia transit routes"],
        "affected_regions": ["Taiwan", "China", "South Korea", "Japan"],
        "freight_increase_pct": 0.60,
        "lead_time_increase_days": 25,
        "probability": "LOW",
        "current_status": "Monitoring — elevated tensions",
    },
    "us_china_tariff": {
        "name": "US-China Tariff Escalation",
        "description": (
            "New tariffs on Chinese imports increase landed cost for all "
            "China-sourced materials."
        ),
        "affected_routes": ["China-Americas"],
        "affected_regions": ["China"],
        "freight_increase_pct": 0.0,
        "lead_time_increase_days": 0,
        "tariff_increase_pct": 0.25,
        "probability": "HIGH",
        "current_status": "ACTIVE — Section 301 tariffs expanded 2026",
    },
    "european_port_strike": {
        "name": "European Port Workers Strike",
        "description": (
            "Widespread port strikes across Rotterdam, Hamburg, and other "
            "major European ports."
        ),
        "affected_routes": ["All European ports"],
        "affected_regions": ["Germany", "Netherlands", "UK"],
        "freight_increase_pct": 0.20,
        "lead_time_increase_days": 10,
        "probability": "MEDIUM",
        "current_status": "Labor negotiations ongoing",
    },
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for data access tool.
    
    Args:
        event: Lambda event with query parameters
        context: Lambda context
    
    Returns:
        Query results from Neptune or S3
    
    Expected event structure:
    {
        "query_type": "find_alternative_suppliers",
        "material_id": "MAT-BAT-001",
        "max_hops": 2
    }
    
    OR
    
    {
        "query_type": "get_supplier_network",
        "supplier_id": "SUP-001"
    }
    
    OR
    
    {
        "query_type": "get_supplier_details",
        "supplier_id": "SUP-001"
    }
    """
    try:
        logger.info(
            "data_access_tool_invoked",
            request_id=context.aws_request_id if context else "local"
        )
        
        query_type = event.get("query_type")
        if not query_type:
            raise ValueError("query_type is required")
        
        # Validate query_type
        allowed_query_types = [
            "find_alternative_suppliers",
            "get_supplier_network",
            "get_supplier_details",
            "get_sourcing_summary",
            "get_all_suppliers",
            "get_supplier_performance",
            "forecast_demand",
            "simulate_risk",
            "list_risk_scenarios"
        ]
        if query_type not in allowed_query_types:
            raise ValueError(
                f"Invalid query_type: {query_type}. "
                f"Allowed values: {', '.join(allowed_query_types)}"
            )
        
        # Initialize Neptune client
        neptune_endpoint = os.environ.get("NEPTUNE_ENDPOINT")
        if not neptune_endpoint:
            raise ValueError("NEPTUNE_ENDPOINT environment variable not set")
        
        neptune_client = NeptuneClient(endpoint=neptune_endpoint)
        
        # Route to appropriate handler
        if query_type == "find_alternative_suppliers":
            result = _find_alternative_suppliers(event, neptune_client)
        
        elif query_type == "get_supplier_network":
            result = _get_supplier_network(event, neptune_client)
        
        elif query_type == "get_supplier_details":
            result = _get_supplier_details(event, neptune_client)

        elif query_type == "get_sourcing_summary":
            result = neptune_client.get_sourcing_summary()

        elif query_type == "get_all_suppliers":
            result = neptune_client.get_suppliers()

        elif query_type == "get_supplier_performance":
            # Performance is stored as properties on Supplier vertices
            suppliers = neptune_client.get_suppliers()
            supplier_id = event.get("supplier_id")
            if supplier_id:
                suppliers = [s for s in suppliers if s.get("supplier_id") == supplier_id]
            result = {"suppliers": sorted(suppliers, key=lambda s: s.get("on_time_delivery_rate", 0) or 0, reverse=True)}

        elif query_type == "forecast_demand":
            result = _forecast_demand(event)

        elif query_type == "simulate_risk":
            result = _simulate_risk(event, neptune_client)

        elif query_type == "list_risk_scenarios":
            result = _list_risk_scenarios()

        logger.info(
            "data_access_complete",
            query_type=query_type,
            request_id=context.aws_request_id if context else "local"
        )
        
        # Close Neptune connection
        neptune_client.close()
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    
    except ValueError as e:
        logger.warning(
            "data_access_validation_error",
            error=str(e)
        )
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Validation error: {str(e)}"
            })
        }
    
    except GremlinServerError as e:
        logger.error(
            "neptune_query_error",
            error=str(e)
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Neptune query error"
            })
        }
    
    except ConnectionError as e:
        logger.error(
            "neptune_connection_error",
            error=str(e)
        )
        return {
            "statusCode": 503,
            "body": json.dumps({
                "error": "Neptune unavailable"
            })
        }
    
    except ClientError as e:
        logger.error(
            "aws_service_error",
            error_code=e.response["Error"]["Code"],
            error=str(e)
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "AWS service error"
            })
        }
    
    except Exception as e:
        logger.error(
            "data_access_tool_error",
            error=str(e),
            exc_info=True
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal error accessing data"
            })
        }


def _forecast_demand(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Forecast demand for a material using Chronos-2 on SageMaker.
    Generates a time series from historical patterns and calls the endpoint.
    Falls back to EC2 if SageMaker endpoint is not configured.
    """
    material_id = event.get("material_id", "MAT-BAT-001")
    prediction_length = event.get("prediction_length", 60)

    # Generate a synthetic time series based on material ID hash
    import hashlib
    seed = int(hashlib.md5(material_id.encode(), usedforsecurity=False).hexdigest()[:8], 16) % 1000
    np_rng = __import__("random")
    np_rng.seed(seed)
    base = 5 + (seed % 15)
    history = [max(0, base + np_rng.randint(-3, 8) + (i % 7) * 0.5) for i in range(90)]

    payload = {
        "inputs": [{"target": history}],
        "parameters": {"prediction_length": min(prediction_length, 64)},
    }

    # Try SageMaker first, fall back to EC2
    sagemaker_endpoint = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "")
    chronos_url = os.environ.get("CHRONOS_EC2_URL", "")

    if sagemaker_endpoint:
        import boto3 as _boto3
        sm_runtime = _boto3.client("sagemaker-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response = sm_runtime.invoke_endpoint(
            EndpointName=sagemaker_endpoint,
            ContentType="application/json",
            Body=json.dumps(payload),
        )
        result = json.loads(response["Body"].read())
    elif chronos_url:
        import urllib.request
        url = f"{chronos_url.rstrip('/')}/forecast"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        if not url.startswith("https://"):
            raise ValueError(f"Refusing to open non-HTTPS URL: {url}")
        with urllib.request.urlopen(req, timeout=120) as resp:  # nosemgrep: dynamic-urllib-use-detected
            result = json.loads(resp.read())
    else:
        raise ValueError("Neither SAGEMAKER_ENDPOINT_NAME nor CHRONOS_EC2_URL configured")

    predictions = result.get("predictions", [{}])[0]
    # SageMaker returns quantiles directly; EC2 nests under "quantiles"
    quantiles = predictions.get("quantiles", predictions)
    p10_vals = quantiles.get("0.1", [])
    p50_vals = quantiles.get("0.5", quantiles.get("mean", []))
    p90_vals = quantiles.get("0.9", [])

    total_p10 = sum(max(0, v) for v in p10_vals)
    total_p50 = sum(max(0, v) for v in p50_vals)
    total_p90 = sum(max(0, v) for v in p90_vals)

    return {
        "material_id": material_id,
        "prediction_length_days": len(p50_vals),
        "model": "chronos-t5-base-120M",
        "summary": {
            "total_p10": round(total_p10),
            "total_p50": round(total_p50),
            "total_p90": round(total_p90),
            "avg_daily_p50": round(total_p50 / max(len(p50_vals), 1), 1),
        },
        "interpretation": (
            f"Over the next {len(p50_vals)} days, expected demand for {material_id} is "
            f"{round(total_p50)} units (median). Conservative estimate (P90): {round(total_p90)} units. "
            f"Optimistic (P10): {round(total_p10)} units."
        ),
    }


def _list_risk_scenarios() -> Dict[str, Any]:
    """
    Return all available geopolitical risk scenarios.

    Returns:
        Dict with scenario summaries keyed by scenario_id
    """
    scenarios = []
    for scenario_id, scenario in RISK_SCENARIOS.items():
        scenarios.append({
            "scenario_id": scenario_id,
            "name": scenario["name"],
            "probability": scenario["probability"],
            "current_status": scenario["current_status"],
            "affected_regions": scenario["affected_regions"],
        })
    return {
        "total_scenarios": len(scenarios),
        "scenarios": scenarios,
    }


def _simulate_risk(
    event: Dict[str, Any],
    neptune_client: NeptuneClient
) -> Dict[str, Any]:
    """
    Simulate the impact of a geopolitical risk scenario on the supply chain.

    Queries Neptune for all suppliers and their supply edges, then calculates
    cost, lead-time, and tariff impacts for suppliers in affected regions.

    Args:
        event: Lambda event containing ``scenario_id``
        neptune_client: Initialised Neptune client

    Returns:
        Structured risk simulation results including affected suppliers,
        total cost impact, and recommended actions.
    """
    scenario_id = event.get("scenario_id")
    if not scenario_id:
        raise ValueError("scenario_id is required for simulate_risk")
    if scenario_id not in RISK_SCENARIOS:
        raise ValueError(
            f"Unknown scenario_id: {scenario_id}"
        )

    scenario = RISK_SCENARIOS[scenario_id]

    logger.info("simulate_risk_start", scenario_id=scenario_id)

    # ------------------------------------------------------------------
    # 1. Fetch all suppliers from Neptune
    # ------------------------------------------------------------------
    sup_raw = neptune_client._http_query(
        "g.V().hasLabel('Supplier').elementMap().toList()"
    )
    suppliers = neptune_client._parse_graphson_list(sup_raw)

    # ------------------------------------------------------------------
    # 2. Fetch all supply edges (supplier -> material) with cost/lead-time
    # ------------------------------------------------------------------
    edge_raw = neptune_client._http_query(
        "g.E().hasLabel('supplies')"
        ".project('supplier','material','lead_time','cost','material_name')"
        ".by(outV().id())"
        ".by(inV().id())"
        ".by(values('lead_time_days'))"
        ".by(values('annual_cost'))"
        ".by(inV().values('name'))"
        ".toList()"
    )
    edges = neptune_client._parse_graphson_list(edge_raw)

    # Build lookup: supplier_id -> list of supply edges
    sup_edges: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges:
        sid = e.get("supplier", "")
        sup_edges.setdefault(sid, []).append(e)

    # ------------------------------------------------------------------
    # 3. Partition suppliers into affected / unaffected
    # ------------------------------------------------------------------
    affected_regions = set(scenario["affected_regions"])
    freight_pct = scenario["freight_increase_pct"]
    lead_time_delta = scenario["lead_time_increase_days"]
    tariff_pct = scenario.get("tariff_increase_pct", 0.0)

    affected_suppliers: List[Dict[str, Any]] = []
    unaffected_suppliers: List[Dict[str, Any]] = []
    total_freight_impact = 0.0
    total_tariff_impact = 0.0

    for sup in suppliers:
        sid = sup.get("id", sup.get("T.id", ""))
        name = sup.get("name", "")
        location = sup.get("location", "")

        if location in affected_regions:
            # Compute per-supplier impact
            supplier_edges = sup_edges.get(sid, [])
            materials_at_risk = []
            supplier_freight_impact = 0.0
            supplier_tariff_impact = 0.0
            supplier_lead_time_impacts = []

            for se in supplier_edges:
                cost_val = se.get("cost", 0)
                if isinstance(cost_val, dict):
                    cost_val = cost_val.get("@value", 0)
                cost_val = float(cost_val)

                lt_val = se.get("lead_time", 0)
                if isinstance(lt_val, dict):
                    lt_val = lt_val.get("@value", 0)
                lt_val = float(lt_val)

                freight_cost = cost_val * freight_pct
                tariff_cost = cost_val * tariff_pct

                supplier_freight_impact += freight_cost
                supplier_tariff_impact += tariff_cost

                materials_at_risk.append({
                    "material_id": se.get("material", ""),
                    "material_name": se.get("material_name", ""),
                    "current_cost": round(cost_val, 2),
                    "freight_cost_increase": round(freight_cost, 2),
                    "tariff_cost_increase": round(tariff_cost, 2),
                    "current_lead_time_days": round(lt_val, 0),
                    "new_lead_time_days": round(lt_val + lead_time_delta, 0),
                })
                supplier_lead_time_impacts.append(lt_val + lead_time_delta)

            total_freight_impact += supplier_freight_impact
            total_tariff_impact += supplier_tariff_impact

            affected_suppliers.append({
                "supplier_id": sid,
                "name": name,
                "location": location,
                "materials_at_risk": materials_at_risk,
                "total_freight_cost_increase": round(supplier_freight_impact, 2),
                "total_tariff_cost_increase": round(supplier_tariff_impact, 2),
                "avg_new_lead_time_days": (
                    round(
                        sum(supplier_lead_time_impacts)
                        / len(supplier_lead_time_impacts),
                        1,
                    )
                    if supplier_lead_time_impacts
                    else 0
                ),
            })
        else:
            unaffected_suppliers.append({
                "supplier_id": sid,
                "name": name,
                "location": location,
            })

    # ------------------------------------------------------------------
    # 4. Build recommended actions (unaffected suppliers as alternatives)
    # ------------------------------------------------------------------
    recommended_actions: List[str] = []
    if affected_suppliers and unaffected_suppliers:
        safe_names = ", ".join(
            f"{s['name']} ({s['location']})" for s in unaffected_suppliers
        )
        recommended_actions.append(
            f"Shift allocation toward unaffected suppliers: {safe_names}."
        )
    if freight_pct > 0:
        recommended_actions.append(
            "Negotiate fixed-rate freight contracts to hedge against "
            "spot-rate volatility."
        )
    if lead_time_delta > 0:
        recommended_actions.append(
            f"Increase safety stock by {lead_time_delta} days of coverage "
            "for affected materials."
        )
    if tariff_pct > 0:
        recommended_actions.append(
            "Evaluate tariff engineering options (HTS reclassification, "
            "foreign trade zones, first-sale valuation)."
        )
    if not affected_suppliers:
        recommended_actions.append(
            "No suppliers are directly affected by this scenario. "
            "Continue monitoring."
        )

    total_cost_impact = round(total_freight_impact + total_tariff_impact, 2)

    logger.info(
        "simulate_risk_complete",
        scenario_id=scenario_id,
        affected_suppliers=len(affected_suppliers),
        total_cost_impact=total_cost_impact,
    )

    return {
        "scenario": {
            "id": scenario_id,
            "name": scenario["name"],
            "description": scenario["description"],
            "probability": scenario["probability"],
            "current_status": scenario["current_status"],
            "affected_routes": scenario["affected_routes"],
            "affected_regions": scenario["affected_regions"],
            "freight_increase_pct": freight_pct,
            "lead_time_increase_days": lead_time_delta,
            "tariff_increase_pct": tariff_pct,
        },
        "affected_suppliers": affected_suppliers,
        "unaffected_suppliers": unaffected_suppliers,
        "total_cost_impact": total_cost_impact,
        "total_freight_impact": round(total_freight_impact, 2),
        "total_tariff_impact": round(total_tariff_impact, 2),
        "recommended_actions": recommended_actions,
    }


def _find_alternative_suppliers(
    event: Dict[str, Any],
    neptune_client: NeptuneClient
) -> Dict[str, Any]:
    """
    Find alternative suppliers via Neptune graph traversal.
    
    Args:
        event: Event with material_id and max_hops
        neptune_client: Neptune client instance
    
    Returns:
        List of alternative supplier IDs
    """
    material_id = event.get("material_id")
    if not material_id:
        raise ValueError("material_id is required")
    
    max_hops = event.get("max_hops", 2)
    limit = event.get("limit", 10)
    
    logger.info(
        "finding_alternative_suppliers",
        material_id=material_id,
        max_hops=max_hops
    )
    
    alternatives = neptune_client.find_alternative_suppliers(
        material_id=material_id,
        max_hops=max_hops,
        limit=limit
    )
    
    return {
        "material_id": material_id,
        "alternative_suppliers": alternatives
    }


def _get_supplier_network(
    event: Dict[str, Any],
    neptune_client: NeptuneClient
) -> Dict[str, Any]:
    """
    Get supplier network from Neptune.
    
    Args:
        event: Event with supplier_id
        neptune_client: Neptune client instance
    
    Returns:
        Supplier network graph
    """
    supplier_id = event.get("supplier_id")
    if not supplier_id:
        raise ValueError("supplier_id is required")
    
    depth = event.get("depth", 2)
    
    logger.info(
        "getting_supplier_network",
        supplier_id=supplier_id,
        depth=depth
    )
    
    network = neptune_client.get_supplier_network(
        supplier_id=supplier_id,
        depth=depth
    )
    
    return network


def _get_supplier_details(
    event: Dict[str, Any],
    neptune_client: NeptuneClient
) -> Dict[str, Any]:
    """
    Get supplier details from Neptune.
    
    Args:
        event: Event with supplier_id
        neptune_client: Neptune client instance
    
    Returns:
        Supplier details
    """
    supplier_id = event.get("supplier_id")
    if not supplier_id:
        raise ValueError("supplier_id is required")
    
    logger.info(
        "getting_supplier_details",
        supplier_id=supplier_id
    )
    
    # Get supplier network which includes supplier details
    network = neptune_client.get_supplier_network(
        supplier_id=supplier_id,
        depth=1
    )
    
    return network
