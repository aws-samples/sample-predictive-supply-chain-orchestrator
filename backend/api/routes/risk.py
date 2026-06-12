from flask import Blueprint, jsonify, request
from typing import Dict, Any
import structlog

from api.state import neptune_client

logger = structlog.get_logger()

risk_bp = Blueprint("risk", __name__)

# ── Domain-specific constants ──

RISK_SCENARIOS = {
    "strait_of_hormuz": {
        "name": "Strait of Hormuz Blockade",
        "description": "Military conflict or blockade disrupts shipping through the Strait of Hormuz, affecting Asia-Europe and Asia-Americas maritime routes.",
        "affected_regions": ["China", "South Korea", "Japan", "Taiwan"],
        "freight_increase_pct": 0.45,
        "lead_time_increase_days": 18,
        "tariff_increase_pct": 0.0,
        "probability": "HIGH",
        "current_status": "ACTIVE — Iran conflict escalation, April 2026",
    },
    "suez_canal": {
        "name": "Suez Canal Disruption",
        "description": "Blockage or Houthi attacks force rerouting around Cape of Good Hope.",
        "affected_regions": ["China", "South Korea", "Japan", "Taiwan"],
        "freight_increase_pct": 0.35,
        "lead_time_increase_days": 14,
        "tariff_increase_pct": 0.0,
        "probability": "MEDIUM",
        "current_status": "Houthi attacks ongoing since 2024",
    },
    "taiwan_strait": {
        "name": "Taiwan Strait Crisis",
        "description": "Military tensions or blockade in the Taiwan Strait disrupts all shipping to/from Taiwan and nearby routes.",
        "affected_regions": ["Taiwan", "China", "South Korea", "Japan"],
        "freight_increase_pct": 0.60,
        "lead_time_increase_days": 25,
        "tariff_increase_pct": 0.0,
        "probability": "LOW",
        "current_status": "Monitoring — elevated tensions",
    },
    "us_china_tariff": {
        "name": "US-China Tariff Escalation",
        "description": "New tariffs on Chinese imports increase landed cost for all China-sourced materials.",
        "affected_regions": ["China"],
        "freight_increase_pct": 0.0,
        "lead_time_increase_days": 0,
        "tariff_increase_pct": 0.25,
        "probability": "HIGH",
        "current_status": "ACTIVE — Section 301 tariffs expanded 2026",
    },
    "european_port_strike": {
        "name": "European Port Workers Strike",
        "description": "Widespread port strikes across Rotterdam, Hamburg, and other major European ports.",
        "affected_regions": ["Germany", "Netherlands", "UK"],
        "freight_increase_pct": 0.20,
        "lead_time_increase_days": 10,
        "tariff_increase_pct": 0.0,
        "probability": "MEDIUM",
        "current_status": "Labor negotiations ongoing",
    },
}

# Supplier region mapping (matches Neptune data)
_SUPPLIER_REGIONS = {
    "SUP-001": ("Shenzhen LiPower Energy Co.", "China"),
    "SUP-002": ("Samsung SDI", "South Korea"),
    "SUP-003": ("Panasonic Energy", "USA"),
    "SUP-004": ("Bafang Electric", "China"),
    "SUP-005": ("Shimano Components", "Taiwan"),
    "SUP-006": ("Bosch eBike Systems", "Germany"),
    "SUP-007": ("Giant Manufacturing", "USA"),
    "SUP-008": ("Merida Industry", "Japan"),
    "SUP-009": ("Reynolds Technology", "UK"),
    "SUP-010": ("Garmin Display Systems", "USA"),
    "SUP-011": ("Continental Electronics", "USA"),
    "SUP-012": ("Sigma Sport", "Germany"),
    "SUP-013": ("DT Swiss AG", "Netherlands"),
    "SUP-014": ("Mavic SAS", "Germany"),
    "SUP-015": ("SRAM Corporation", "Germany"),
}

# Material supply mapping
_SUPPLIER_MATERIALS = {
    "SUP-001": ["MAT-BAT-001", "MAT-BAT-002", "MAT-BAT-003"],
    "SUP-002": ["MAT-BAT-001", "MAT-BAT-002", "MAT-BAT-003"],
    "SUP-003": ["MAT-BAT-001", "MAT-BAT-002", "MAT-BAT-003"],
    "SUP-004": ["MAT-MOT-001", "MAT-MOT-002", "MAT-MOT-003", "MAT-MOT-004"],
    "SUP-005": ["MAT-MOT-001", "MAT-MOT-002", "MAT-MOT-003", "MAT-MOT-004"],
    "SUP-006": ["MAT-MOT-001", "MAT-MOT-002"],
    "SUP-007": ["MAT-FRM-001", "MAT-FRM-003", "MAT-FRM-004"],
    "SUP-008": ["MAT-FRM-002"],
    "SUP-009": ["MAT-FRM-001", "MAT-FRM-002", "MAT-FRM-003", "MAT-FRM-004"],
    "SUP-010": ["MAT-ELC-001", "MAT-ELC-002", "MAT-ELC-003"],
    "SUP-011": ["MAT-ELC-001", "MAT-ELC-002", "MAT-ELC-003"],
    "SUP-012": ["MAT-ELC-001"],
    "SUP-013": ["MAT-STD-001", "MAT-STD-003", "MAT-STD-004"],
    "SUP-014": ["MAT-STD-001", "MAT-STD-002", "MAT-STD-003", "MAT-STD-004"],
    "SUP-015": ["MAT-STD-002"],
}


@risk_bp.route("/api/risk-simulation", methods=["POST"])
def risk_simulation():
    """Simulate geopolitical risk impact — queries Neptune for live supplier data."""
    try:
        data = request.get_json(force=True)
        scenario_id = data.get("scenario_id", "")
        if not scenario_id:
            return jsonify({"error": "scenario_id is required"}), 400

        if scenario_id == "list":
            return jsonify({
                "scenarios": [
                    {"id": k, "name": v["name"], "probability": v["probability"], "status": v["current_status"]}
                    for k, v in RISK_SCENARIOS.items()
                ]
            })

        if scenario_id not in RISK_SCENARIOS:
            return jsonify({"error": f"Unknown scenario: {scenario_id}"}), 400

        scenario = RISK_SCENARIOS[scenario_id]
        affected_regions = set(scenario["affected_regions"])

        # Query Neptune for live supplier + material data
        suppliers_data = []
        edges_data = []
        if neptune_client:
            try:
                sup_raw = neptune_client._http_query("g.V().hasLabel('Supplier').elementMap().toList()")
                suppliers_data = neptune_client._parse_graphson_list(sup_raw)
                edge_raw = neptune_client._http_query(
                    "g.E().hasLabel('supplies').project('supplier','material')"
                    ".by(outV().id()).by(inV().id()).toList()"
                )
                edges_data = neptune_client._parse_graphson_list(edge_raw)
                logger.info("risk_sim_neptune_data", suppliers=len(suppliers_data), edges=len(edges_data))
            except (ConnectionError, OSError, ValueError) as e:
                logger.warning("risk_sim_neptune_failed_using_fallback", error=str(e))

        # Build supplier-materials map from Neptune edges
        sup_materials: Dict[str, list] = {}
        for edge in edges_data:
            sid = edge.get("supplier", "")
            mid = edge.get("material", "")
            sup_materials.setdefault(sid, []).append(mid)

        affected_suppliers = []
        unaffected_suppliers = []

        for sup in suppliers_data:
            sup_id = sup.get("id", sup.get("T.id", ""))
            name = sup.get("name", sup_id)
            location = sup.get("location", "Unknown")
            materials = sup_materials.get(sup_id, [])

            # Check if supplier's location matches affected regions
            region_match = any(r.lower() in location.lower() for r in affected_regions)

            if region_match:
                freight_impact = scenario["freight_increase_pct"] * 100
                tariff_impact = scenario.get("tariff_increase_pct", 0) * 100
                affected_suppliers.append({
                    "supplier_id": sup_id,
                    "name": name,
                    "location": location,
                    "materials_at_risk": materials,
                    "materials_count": len(materials),
                    "freight_increase_pct": freight_impact,
                    "tariff_increase_pct": tariff_impact,
                    "lead_time_increase_days": scenario["lead_time_increase_days"],
                    "estimated_cost_impact_pct": freight_impact + tariff_impact,
                })
            else:
                unaffected_suppliers.append({
                    "supplier_id": sup_id,
                    "name": name,
                    "location": location,
                    "materials_supplied": materials,
                    "status": "SAFE",
                })

        # If Neptune returned no data, fall back to hardcoded mapping
        if not suppliers_data:
            logger.info("risk_sim_using_hardcoded_fallback")
            for sup_id, (name, region) in _SUPPLIER_REGIONS.items():
                materials = _SUPPLIER_MATERIALS.get(sup_id, [])
                if region in affected_regions:
                    freight_impact = scenario["freight_increase_pct"] * 100
                    tariff_impact = scenario.get("tariff_increase_pct", 0) * 100
                    affected_suppliers.append({
                        "supplier_id": sup_id, "name": name, "location": region,
                        "materials_at_risk": materials, "materials_count": len(materials),
                        "freight_increase_pct": freight_impact, "tariff_increase_pct": tariff_impact,
                        "lead_time_increase_days": scenario["lead_time_increase_days"],
                        "estimated_cost_impact_pct": freight_impact + tariff_impact,
                    })
                else:
                    unaffected_suppliers.append({
                        "supplier_id": sup_id, "name": name, "location": region,
                        "materials_supplied": materials, "status": "SAFE",
                    })

        # Calculate totals
        total_materials_at_risk = len(set(m for s in affected_suppliers for m in s["materials_at_risk"]))
        avg_cost_impact = sum(s["estimated_cost_impact_pct"] for s in affected_suppliers) / max(len(affected_suppliers), 1)

        # Build recommendations
        actions = []
        if affected_suppliers:
            safe_names = [s["name"] for s in unaffected_suppliers[:3]]
            actions.append(f"Shift orders to unaffected suppliers: {', '.join(safe_names)}")
            actions.append(f"Pre-order {scenario['lead_time_increase_days'] + 14} days of safety stock for affected materials")
        if scenario.get("tariff_increase_pct", 0) > 0:
            actions.append("Evaluate tariff exemption applications or bonded warehouse options")
        actions.append("Re-run procurement optimization with updated freight rates and lead times")
        actions.append(f"Monitor {scenario['current_status']} for escalation indicators")

        data_source = "neptune" if suppliers_data else "fallback"

        return jsonify({
            "scenario": {
                "id": scenario_id,
                "name": scenario["name"],
                "description": scenario["description"],
                "probability": scenario["probability"],
                "current_status": scenario["current_status"],
                "freight_increase_pct": scenario["freight_increase_pct"] * 100,
                "lead_time_increase_days": scenario["lead_time_increase_days"],
                "tariff_increase_pct": scenario.get("tariff_increase_pct", 0) * 100,
            },
            "affected_suppliers": affected_suppliers,
            "unaffected_suppliers": unaffected_suppliers,
            "summary": {
                "affected_supplier_count": len(affected_suppliers),
                "unaffected_supplier_count": len(unaffected_suppliers),
                "total_materials_at_risk": total_materials_at_risk,
                "avg_cost_impact_pct": round(avg_cost_impact, 1),
                "max_lead_time_increase_days": scenario["lead_time_increase_days"],
            },
            "recommended_actions": actions,
            "data_source": data_source,
        })
    except (ValueError, KeyError, TypeError) as e:
        logger.error("risk_simulation_error", error=str(e))
        return jsonify({"error": "Risk simulation failed. Please try again."}), 500
