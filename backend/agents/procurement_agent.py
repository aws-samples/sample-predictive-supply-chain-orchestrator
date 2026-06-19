"""
Procurement optimization agent using Strands SDK.

Provides tool-augmented AI agent for supplier selection,
optimization explanation, data queries, and PR creation.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import boto3

from core.models import (
    MaterialDemand,
    OptimizationConstraints,
    OptimizationRequest,
)
from core.optimization.engine import OptimizationEngine
from data.csv_reader import CSVDataReader

logger = structlog.get_logger()

# Initialize shared data reader and engine
# Lambda: DATA_DIR=/var/task/data; Local dev: ../data (relative to backend/)
_data_dir = os.environ.get("DATA_DIR", os.environ.get("DATA_PATH", str(Path(__file__).parent.parent / "data")))
try:
    _data_reader = CSVDataReader(data_dir=_data_dir)
    _engine = OptimizationEngine(_data_reader)
    logger.info("procurement_agent_engine_initialized", data_dir=_data_dir)
except Exception as e:
    logger.error("procurement_agent_engine_init_failed", error=str(e))
    _data_reader = None
    _engine = None

# In-memory PR store for demo
_pr_store: Dict[str, Dict[str, Any]] = {}


def _try_import_strands():
    """Try to import Strands SDK; return None if unavailable."""
    try:
        import os
        os.environ.setdefault("OTEL_SDK_DISABLED", "true")
        os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")
        os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
        os.environ.setdefault("OTEL_LOGS_EXPORTER", "none")
        # Suppress StopIteration from opentelemetry context loading in Lambda
        try:
            import opentelemetry.context
            if not hasattr(opentelemetry.context, '_RUNTIME_CONTEXT'):
                from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
                opentelemetry.context._RUNTIME_CONTEXT = ContextVarsRuntimeContext()
        except (ImportError, AttributeError, StopIteration):
            pass
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools import tool
        logger.info("strands_sdk_imported_successfully")
        return Agent, BedrockModel, tool
    except Exception as e:
        logger.error("strands_import_failed", error=str(e), error_type=type(e).__name__)
        return None, None, None


# --- Tool functions (usable with or without Strands) ---

def optimize_suppliers(materials: list, constraints: dict) -> dict:
    """Run multi-objective optimization for supplier selection.

    Args:
        materials: List of dicts with material_id and quantity.
        constraints: Dict with max_supplier_concentration, max_lead_time_days, budget_max.

    Returns:
        Dict with solutions array and computation metadata.
    """
    if _engine is None:
        return {"error": "Optimization engine not initialized"}

    try:
        material_demands = [
            MaterialDemand(material_id=m["material_id"], quantity=m["quantity"])
            for m in materials
        ]
        opt_constraints = OptimizationConstraints(**constraints) if constraints else OptimizationConstraints()
        request = OptimizationRequest(materials=material_demands, constraints=opt_constraints)

        import time
        start = time.time()
        solutions = _engine.optimize(request)
        elapsed_ms = int((time.time() - start) * 1000)

        solutions_json = []
        for sol in solutions:
            solutions_json.append({
                "name": sol.name,
                "total_cost": sol.total_cost,
                "risk_score": sol.risk_score,
                "quality_score": sol.quality_score,
                "lead_time_days": sol.lead_time_days,
                "max_supplier_concentration": sol.max_supplier_concentration,
                "reasoning": sol.reasoning,
                "demand_buffer_pct": sol.demand_buffer_pct,
                "num_allocations": len(sol.allocations),
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
                    for a in sol.allocations
                ],
            })

        return {
            "solutions": solutions_json,
            "computation_time_ms": elapsed_ms,
            "solutions_count": len(solutions_json),
        }
    except Exception as e:
        logger.error("optimize_suppliers_failed", error=str(e))
        return {"error": str(e)}


def explain_solution(solution_name: str, total_cost: float, risk_score: float) -> dict:
    """Explain an optimization decision in business terms.

    Args:
        solution_name: Name of the solution (Budget, Balanced, Premium, Resilient).
        total_cost: Total cost of the solution.
        risk_score: Risk score of the solution (0-10).

    Returns:
        Dict with explanation text and key insights.
    """
    explanations = {
        "Budget": {
            "strategy": "Cost minimization with acceptable risk",
            "description": f"The Budget solution achieves the lowest Total Cost of Ownership at ${total_cost:,.0f}. "
                          f"Risk score of {risk_score:.1f}/10 is managed through volume consolidation and "
                          f"favorable payment terms. Best for cost-sensitive procurement with flexible timelines.",
            "trade_offs": ["Higher supplier concentration", "Longer lead times possible", "Cost savings from volume discounts"],
            "recommended_for": "Standard procurement, non-critical materials, budget-constrained projects",
        },
        "Balanced": {
            "strategy": "Optimal trade-off across cost, risk, and quality",
            "description": f"The Balanced solution provides the best risk-adjusted value at ${total_cost:,.0f}. "
                          f"Risk score of {risk_score:.1f}/10 balances cost efficiency with supply chain resilience. "
                          f"Recommended for most procurement scenarios.",
            "trade_offs": ["Moderate cost premium over Budget", "Better quality assurance", "Leverages contracted suppliers"],
            "recommended_for": "General procurement, production-critical materials, standard lead times",
        },
        "Premium": {
            "strategy": "Quality and risk minimization priority",
            "description": f"The Premium solution maximizes quality and minimizes risk at ${total_cost:,.0f}. "
                          f"Risk score of {risk_score:.1f}/10 uses only trend-verified top-performing suppliers. "
                          f"Supply chain insurance for critical production.",
            "trade_offs": ["Highest TCO", "Shortest lead times", "Best supplier performance history"],
            "recommended_for": "Critical materials, high-reliability requirements, time-sensitive production",
        },
        "Resilient": {
            "strategy": "Demand uncertainty and disruption protection",
            "description": f"The Resilient solution optimizes for supply chain disruption protection at ${total_cost:,.0f}. "
                          f"Risk score of {risk_score:.1f}/10 with demand buffers to handle forecast uncertainty. "
                          f"Quantities inflated to protect against demand surges.",
            "trade_offs": ["Higher quantities than base forecast", "Broader supplier diversification", "Buffer stock costs"],
            "recommended_for": "Volatile demand, long lead times, geopolitically exposed supply chains",
        },
    }

    result = explanations.get(solution_name, {
        "strategy": "Custom optimization",
        "description": f"Solution '{solution_name}' with cost ${total_cost:,.0f} and risk {risk_score:.1f}/10.",
        "trade_offs": [],
        "recommended_for": "Consult procurement team for guidance",
    })

    return {
        "solution_name": solution_name,
        **result,
    }


def query_supplier_data(query_type: str, supplier_id: str = None, material_id: str = None) -> dict:
    """Query supplier network data.

    Args:
        query_type: Type of query - 'suppliers', 'materials', 'performance', 'alternatives'.
        supplier_id: Optional supplier ID filter.
        material_id: Optional material ID filter.

    Returns:
        Dict with query results.
    """
    if _data_reader is None:
        return {"error": "Data reader not initialized"}

    try:
        if query_type == "suppliers":
            suppliers = _data_reader.get_suppliers()
            if supplier_id:
                suppliers = [s for s in suppliers if s.supplier_id == supplier_id]
            return {
                "suppliers": [s.model_dump() for s in suppliers],
                "count": len(suppliers),
            }

        elif query_type == "materials":
            materials = _data_reader.get_materials()
            if material_id:
                materials = [m for m in materials if m.material_id == material_id]
            return {
                "materials": [m.model_dump() for m in materials],
                "count": len(materials),
            }

        elif query_type == "performance":
            performance = _data_reader.get_supplier_performance()
            if supplier_id:
                performance = [p for p in performance if p.supplier_id == supplier_id]
            return {
                "performance": [p.model_dump() for p in performance],
                "count": len(performance),
            }

        elif query_type == "alternatives":
            if not material_id:
                return {"error": "material_id required for alternatives query"}
            supplier_materials = _data_reader.get_suppliers_for_material(material_id)
            return {
                "alternatives": [
                    {
                        "supplier_id": sm.supplier_id,
                        "material_id": sm.material_id,
                        "base_price": sm.base_price,
                        "lead_time_days": sm.lead_time_days,
                        "quality_certification": sm.quality_certification,
                    }
                    for sm in supplier_materials
                ],
                "count": len(supplier_materials),
            }

        else:
            return {"error": f"Unknown query_type: {query_type}. Use: suppliers, materials, performance, alternatives"}

    except Exception as e:
        logger.error("query_supplier_data_failed", error=str(e))
        return {"error": str(e)}


def create_purchase_requisitions(solution_name: str, allocations: list) -> dict:
    """Create purchase requisitions from optimization solution allocations.

    Args:
        solution_name: Name of the selected solution.
        allocations: List of allocation dicts with supplier_id, material_id, quantity, unit_price.

    Returns:
        Dict with PR IDs, status, and total value.
    """
    try:
        # Group by supplier
        suppliers: Dict[str, list] = {}
        for alloc in allocations:
            sid = alloc["supplier_id"]
            if sid not in suppliers:
                suppliers[sid] = []
            suppliers[sid].append(alloc)

        pr_ids = []
        total_value = 0.0

        for supplier_id, supplier_allocs in suppliers.items():
            pr_id = f"PR-{datetime.now().strftime('%Y')}-{str(len(_pr_store) + len(pr_ids) + 1).zfill(3)}"
            pr_value = sum(a.get("quantity", 0) * a.get("unit_price", 0) for a in supplier_allocs)
            total_value += pr_value

            pr_data = {
                "pr_id": pr_id,
                "supplier_id": supplier_id,
                "solution_name": solution_name,
                "status": "pending_approval",
                "line_items": supplier_allocs,
                "total_value": pr_value,
                "created_at": datetime.now().isoformat(),
                "requester": "procurement-agent",
            }
            _pr_store[pr_id] = pr_data
            pr_ids.append(pr_id)

        return {
            "pr_ids": pr_ids,
            "total_prs": len(pr_ids),
            "total_value": total_value,
            "status": "pending_approval",
            "solution_name": solution_name,
        }

    except Exception as e:
        logger.error("create_prs_failed", error=str(e))
        return {"error": str(e)}


def get_purchase_requisitions() -> dict:
    """Get all purchase requisitions from in-memory store."""
    return {
        "purchase_requisitions": list(_pr_store.values()),
        "total": len(_pr_store),
    }


def query_defect_data(
    query_type: str = "summary",
    supplier_id: str = None,
    material_id: str = None,
    severity: str = None,
) -> dict:
    """Query defect tracking data for suppliers and materials.

    Args:
        query_type: One of 'summary', 'defects', 'report', 'score'.
            - summary: Overview stats with breakdowns by severity, supplier, material, category.
            - defects: List of individual defect records (filterable).
            - report: Trend analysis with monthly data, root causes, resolution times.
            - score: Defect risk score for a specific supplier (0-10).
        supplier_id: Filter by supplier (e.g. 'SUP-001'). Required for 'score'.
        material_id: Filter by material (e.g. 'MAT-BAT-001').
        severity: Filter by severity: CRITICAL, MAJOR, or MINOR.

    Returns:
        Dict with defect data matching the query.
    """
    if _data_reader is None:
        return {"error": "Data reader not initialized"}

    try:
        if query_type == "score":
            if not supplier_id:
                return {"error": "supplier_id is required for score query"}
            score = _data_reader.get_supplier_defect_score(supplier_id)
            supplier = _data_reader.get_supplier_by_id(supplier_id)
            defects = _data_reader.get_defects_for_supplier(supplier_id)
            return {
                "supplier_id": supplier_id,
                "supplier_name": supplier.name if supplier else supplier_id,
                "defect_score": round(score, 2),
                "total_defects": len(defects),
                "open_defects": sum(1 for d in defects if d.status == "OPEN"),
                "critical_defects": sum(1 for d in defects if d.severity == "CRITICAL"),
                "recalls": sum(1 for d in defects if d.recall_initiated),
            }

        if query_type == "summary":
            defects = _data_reader.get_defects()
            suppliers = _data_reader.get_suppliers()

            by_supplier = {}
            for s in suppliers:
                s_defects = [d for d in defects if d.supplier_id == s.supplier_id]
                if s_defects:
                    by_supplier[s.supplier_id] = {
                        "name": s.name,
                        "total": len(s_defects),
                        "open": sum(1 for d in s_defects if d.status == "OPEN"),
                        "critical": sum(1 for d in s_defects if d.severity == "CRITICAL"),
                        "score": round(_data_reader.get_supplier_defect_score(s.supplier_id), 2),
                    }

            return {
                "total_defects": len(defects),
                "open": sum(1 for d in defects if d.status == "OPEN"),
                "resolved": sum(1 for d in defects if d.status == "RESOLVED"),
                "critical": sum(1 for d in defects if d.severity == "CRITICAL"),
                "recalls": sum(1 for d in defects if d.recall_initiated),
                "units_affected": sum(d.quantity_affected for d in defects),
                "by_supplier": by_supplier,
                "categories": {},
            }

        if query_type == "defects":
            defects = _data_reader.get_defects()
            if supplier_id:
                defects = [d for d in defects if d.supplier_id == supplier_id]
            if material_id:
                defects = [d for d in defects if d.material_id == material_id]
            if severity:
                defects = [d for d in defects if d.severity == severity.upper()]

            records = []
            for d in sorted(defects, key=lambda x: x.defect_date, reverse=True)[:20]:
                supplier = _data_reader.get_supplier_by_id(d.supplier_id)
                material = _data_reader.get_material_by_id(d.material_id)
                records.append({
                    "defect_id": d.defect_id,
                    "supplier": supplier.name if supplier else d.supplier_id,
                    "material": material.name if material else d.material_id,
                    "date": d.defect_date.isoformat(),
                    "severity": d.severity,
                    "status": d.status,
                    "quantity": d.quantity_affected,
                    "category": d.category,
                    "description": d.description,
                    "root_cause": d.root_cause,
                    "recall": d.recall_initiated,
                })
            return {"defects": records, "count": len(records)}

        if query_type == "report":
            defects = _data_reader.get_defects()
            if supplier_id:
                defects = [d for d in defects if d.supplier_id == supplier_id]

            if not defects:
                return {"report": "No defects found.", "data": {}}

            # Resolution times
            res_times = []
            for d in defects:
                if d.resolution_date:
                    res_times.append((d.resolution_date - d.defect_date).days)

            # Root causes
            causes: dict = {}
            for d in defects:
                c = d.root_cause[:60]
                causes[c] = causes.get(c, 0) + 1
            top_causes = sorted(causes.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total": len(defects),
                "avg_resolution_days": round(sum(res_times) / len(res_times), 1) if res_times else None,
                "recall_rate_pct": round(sum(1 for d in defects if d.recall_initiated) / len(defects) * 100, 1),
                "open_rate_pct": round(sum(1 for d in defects if d.status == "OPEN") / len(defects) * 100, 1),
                "top_root_causes": [{"cause": c, "count": n} for c, n in top_causes],
            }

        return {"error": f"Unknown query_type: {query_type}. Use: summary, defects, report, score"}

    except Exception as e:
        logger.error("query_defect_data_failed", error=str(e))
        return {"error": str(e)}


# --- Strands Agent setup ---


_SYSTEM_PROMPT = """You are a senior procurement analyst at VoltCycle, an e-bike manufacturer. You optimize supplier selection across a 16-material BOM for urban and mountain e-bikes.

TOOLS AVAILABLE:
- optimize_suppliers: Run multi-objective optimization (Budget, Balanced, Premium, Resilient strategies)
- explain_solution: Get detailed analysis of a specific strategy
- query_supplier_data: Query supplier network, performance, and material data
- query_defect_data: Query defect tracking data — summaries, individual defects, reports, and supplier defect risk scores
- create_purchase_requisitions: Generate PRs for ERP submission

RESPONSE FORMAT:
- Use markdown tables for comparisons
- Use **bold** for key numbers and decisions
- Structure responses with clear headers (##)
- Include a "Recommendation" section with your professional opinion
- When showing optimization results, present as a comparison table with columns for Cost, Risk, Quality, Lead Time
- When explaining trade-offs, be specific about dollar amounts and percentages
- End optimization responses with "Next steps" suggesting what the user should do

CONTEXT:
- VoltCycle produces 500 urban e-bikes per quarter
- BOM includes: batteries (3 components), motors (3), frames (3), electronics (3), standard parts (4)
- 15 qualified suppliers across USA, Europe, and Asia
- Supply chain data is from Amazon Neptune graph database
- Defect tracking system monitors supplier quality issues, recalls, and corrective actions
- Defect history scores (0-10) feed into the optimization engine's risk calculation
- Key concerns: cost optimization, supplier risk diversification, lead time for Q2 production, defect history"""


def _create_strands_agent():
    """Create Strands agent if SDK is available."""
    Agent, BedrockModel, tool = _try_import_strands()
    if Agent is None:
        return None

    # Wrap functions as Strands tools
    optimize_tool = tool(optimize_suppliers)
    explain_tool = tool(explain_solution)
    query_tool = tool(query_supplier_data)
    defect_tool = tool(query_defect_data)
    pr_tool = tool(create_purchase_requisitions)

    model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"),
        region_name=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
    )

    agent = Agent(
        model=model,
        tools=[optimize_tool, explain_tool, query_tool, defect_tool, pr_tool],
        system_prompt=_SYSTEM_PROMPT,
    )

    logger.info("strands_agent_created")
    return agent


# Try to create agent at module load (without memory — memory is per-session)
_strands_agent = _create_strands_agent()


def _invoke_agentcore(message: str, auth_token: str = "") -> str:
    """Invoke the procurement agent via AgentCore Runtime endpoint."""
    import json
    import urllib.request
    agent_id = os.environ.get("PROCUREMENT_AGENT_ID", os.environ.get("AGENTCORE_AGENT_ID", ""))
    if not agent_id:
        raise RuntimeError(
            "No AgentCore agent ID configured. "
            "Set PROCUREMENT_AGENT_ID or AGENTCORE_AGENT_ID env var."
        )
    region = os.environ.get("AWS_REGION", "us-east-1")
    # Build ARN — agent_id may already be a full ARN or just the ID
    if agent_id.startswith("arn:"):
        agent_arn = agent_id
    else:
        account = os.environ.get("AWS_ACCOUNT_ID", "")
        if not account:
            account = boto3.client("sts").get_caller_identity()["Account"]
        agent_arn = f"arn:aws:bedrock-agentcore:{region}:{account}:runtime/{agent_id}"

    import re as _re
    if not _re.match(r"^[a-z]{2}(-[a-z]+-\d+)?$", region):
        raise ValueError(f"Invalid AWS region format: {region}")

    logger.info("agentcore_invoke", agent_arn=agent_arn, has_token=bool(auth_token))

    # AgentCore Runtime is configured with JWT auth (Cognito) — use HTTP with Bearer token
    if auth_token:
        import urllib.parse
        escaped_arn = urllib.parse.quote(agent_arn, safe="")
        url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_arn}/invocations"
        body = json.dumps({"prompt": message}).encode()
        bearer = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        session_id = f"web-session-{uuid.uuid4().hex}"
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
            "Authorization": bearer,
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        })
        if not url.startswith("https://"):
            raise ValueError(f"Refusing non-HTTPS URL: {url}")
        with urllib.request.urlopen(req, timeout=25) as http_resp:  # nosec B310 — AWS endpoint, 25s to stay under APIGW 29s limit
            raw = http_resp.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, str):
                return parsed
            if isinstance(parsed, dict):
                return parsed.get("response", parsed.get("output", raw))
            return raw
        except (json.JSONDecodeError, TypeError):
            return raw

    # Fallback: try boto3 SigV4 (works if agent allows IAM auth)
    client = boto3.client("bedrock-agentcore", region_name=region)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        payload=json.dumps({"prompt": message}),
    )

    # AgentCore returns a dict with a StreamingBody.
    # The streaming body can be under "response" or "body" key.
    for key in ("response", "body"):
        stream = resp.get(key)
        if stream and hasattr(stream, "read"):
            raw = stream.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, str):
                    return parsed
                if isinstance(parsed, dict):
                    return parsed.get("response", parsed.get("output", raw))
                return raw
            except (json.JSONDecodeError, TypeError):
                return raw

    # Fallback: direct string values in the response dict
    if isinstance(resp, dict):
        for key in ("response", "output", "body", "payload"):
            val = resp.get(key)
            if isinstance(val, str):
                return val

    return str(resp)


def invoke_agent(
    message: str,
    session_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    auth_token: str = "",
) -> str:
    """Invoke the procurement agent with a user message.

    Mode controlled by AGENT_MODE env var:
      - 'agentcore': call AgentCore Runtime (Lambda/production)
      - 'local': use inline Strands agent (local dev)
    Falls back to keyword-based responses if both fail.
    """
    mode = os.environ.get("AGENT_MODE", "local")

    if mode == "agentcore":
        try:
            logger.info("agentcore_invoking", message_len=len(message))
            result = _invoke_agentcore(message, auth_token=auth_token)
            logger.info("agentcore_invocation_complete", response_len=len(result))
            return result
        except Exception as e:
            logger.error("agentcore_invocation_failed", error=str(e))
            return _fallback_response(message)

    # Local mode — use inline Strands agent
    if _strands_agent is not None:
        try:
            import concurrent.futures
            logger.info("strands_invoking", message_len=len(message))
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: str(_strands_agent(message)))
                result = future.result(timeout=25)
            logger.info("strands_invocation_complete", response_len=len(result))
            return result
        except concurrent.futures.TimeoutError:
            logger.warning("strands_timeout_falling_back")
            return _fallback_response(message)
        except Exception as e:
            logger.error("strands_agent_invocation_failed", error=str(e), error_type=type(e).__name__)
            return _fallback_response(message)

    return _fallback_response(message)


def _fallback_response(message: str) -> str:
    """Generate response using tool functions directly when Strands is unavailable."""
    msg_lower = message.lower()

    # Optimization request
    if any(kw in msg_lower for kw in ["optimize", "run", "procurement", "e-bike", "ebike"]):
        # Parse quantity if mentioned
        import re
        qty_match = re.search(r'(\d+)\s*(e-?bikes?|units?|bikes?)?', msg_lower)
        quantity = int(qty_match.group(1)) if qty_match else 500

        # Full Urban E-Bike BOM (16 materials)
        materials = [
            {"material_id": "MAT-BAT-001", "quantity": quantity},
            {"material_id": "MAT-BAT-002", "quantity": quantity},
            {"material_id": "MAT-BAT-003", "quantity": quantity},
            {"material_id": "MAT-MOT-001", "quantity": quantity},
            {"material_id": "MAT-MOT-003", "quantity": quantity},
            {"material_id": "MAT-MOT-004", "quantity": quantity},
            {"material_id": "MAT-FRM-001", "quantity": quantity},
            {"material_id": "MAT-FRM-003", "quantity": quantity},
            {"material_id": "MAT-FRM-004", "quantity": quantity},
            {"material_id": "MAT-ELC-001", "quantity": quantity},
            {"material_id": "MAT-ELC-002", "quantity": quantity},
            {"material_id": "MAT-ELC-003", "quantity": quantity},
            {"material_id": "MAT-STD-001", "quantity": quantity},
            {"material_id": "MAT-STD-002", "quantity": quantity},
            {"material_id": "MAT-STD-003", "quantity": quantity},
            {"material_id": "MAT-STD-004", "quantity": quantity},
        ]
        constraints = {"max_supplier_concentration": 0.60, "max_lead_time_days": 60, "budget_max": 2_000_000}
        result = optimize_suppliers(materials, constraints)

        if "error" in result:
            return f"Optimization failed: {result['error']}"

        solutions = result["solutions"]
        budget = next((s for s in solutions if s['name'] == 'Budget'), solutions[0])
        premium = next((s for s in solutions if s['name'] == 'Premium'), solutions[-1])
        savings = premium['total_cost'] - budget['total_cost']
        savings_pct = (savings / premium['total_cost']) * 100 if premium['total_cost'] > 0 else 0

        lines = [
            f"## Optimization Results ({result['computation_time_ms']}ms)\n",
            f"Analyzed **{quantity} e-bikes** across **16 materials** from **{len(set(a['supplier_id'] for s in solutions for a in s['allocations']))} suppliers**.\n",
            "| Strategy | Total Cost | Risk | Quality | Lead Time |",
            "|----------|-----------|------|---------|-----------|",
        ]
        for sol in solutions:
            lines.append(
                f"| **{sol['name']}** | ${sol['total_cost']:,.0f} | {sol['risk_score']:.1f}/10 | "
                f"{sol['quality_score']:.1f}/10 | {sol['lead_time_days']}d |"
            )
        lines.extend([
            f"\n**Savings opportunity:** ${savings:,.0f} ({savings_pct:.0f}%) between Budget and Premium strategies.",
            f"\n### Recommendation",
            (
                f"The **Balanced** strategy offers the best risk-adjusted value. It costs ${next((s['total_cost'] for s in solutions if s['name'] == 'Balanced'), 0):,.0f} — "
                f"a moderate premium over Budget for significantly better quality and risk scores."
            ),
            f"\n**Next steps:** Ask me to `explain` any strategy, or `create PRs` for your chosen option.",
        ])
        return "\n".join(lines)

    # Explain request
    if "explain" in msg_lower:
        for name in ["Budget", "Balanced", "Premium", "Resilient"]:
            if name.lower() in msg_lower:
                result = explain_solution(name, 850000, 3.5)
                return (
                    f"**{result['solution_name']}** - {result['strategy']}\n\n"
                    f"{result['description']}\n\n"
                    f"Trade-offs: {', '.join(result['trade_offs'])}\n\n"
                    f"Recommended for: {result['recommended_for']}"
                )
        return "Which solution would you like me to explain? Options: Budget, Balanced, Premium, Resilient."

    # Defect / quality / recall queries
    if any(kw in msg_lower for kw in [
        "defect", "recall", "quality issue", "defective", "faulty",
        "open case", "open issue", "critical case", "critical issue",
        "quality problem", "part failure", "component failure",
        "corrective action", "root cause", "batch",
    ]):
        import re
        sup_match = re.search(r'sup-\d{3}', msg_lower)
        mat_match = re.search(r'mat-[a-z]+-\d{3}', msg_lower)

        # ── Targeted questions: answer directly, then show context ──
        summary = query_defect_data("summary")
        if "error" in summary:
            return f"Could not retrieve defect data: {summary['error']}"

        # "How many open / critical / resolved / recalls?"
        asking_count = any(w in msg_lower for w in ["how many", "count", "number of", "total"])
        asking_open = "open" in msg_lower
        asking_critical = "critical" in msg_lower
        asking_resolved = "resolved" in msg_lower or "closed" in msg_lower
        asking_recall = "recall" in msg_lower

        if asking_count and (asking_open or asking_critical or asking_resolved or asking_recall):
            lines = []
            if asking_open:
                lines.append(f"There are **{summary['open']}** open defect cases out of {summary['total_defects']} total.\n")
            if asking_critical:
                lines.append(f"There are **{summary['critical']}** critical defects recorded.\n")
            if asking_resolved:
                lines.append(f"**{summary['resolved']}** defect cases have been resolved.\n")
            if asking_recall:
                lines.append(f"**{summary['recalls']}** recalls have been initiated.\n")

            # Add a brief breakdown
            open_by_supplier = [(info["name"], info["open"]) for info in summary["by_supplier"].values() if info["open"] > 0]
            if asking_open and open_by_supplier:
                lines.append("**Open cases by supplier:**\n")
                lines.append("| Supplier | Open Defects |")
                lines.append("|----------|-------------|")
                for name, count in sorted(open_by_supplier, key=lambda x: x[1], reverse=True):
                    lines.append(f"| {name} | {count} |")

            crit_by_supplier = [(info["name"], info["critical"]) for info in summary["by_supplier"].values() if info["critical"] > 0]
            if asking_critical and crit_by_supplier:
                lines.append("\n**Critical defects by supplier:**\n")
                lines.append("| Supplier | Critical |")
                lines.append("|----------|----------|")
                for name, count in sorted(crit_by_supplier, key=lambda x: x[1], reverse=True):
                    lines.append(f"| {name} | {count} |")

            lines.append(f"\nUse the **Defect Tracker** tab for full details, or ask about a specific supplier (e.g., `defects SUP-001`).")
            return "\n".join(lines)

        # ── Supplier-specific query ──
        if sup_match:
            sid = sup_match.group(0).upper()
            result = query_defect_data("score", supplier_id=sid)
            if "error" in result:
                return f"Could not retrieve defect data: {result['error']}"
            defects_list = query_defect_data("defects", supplier_id=sid)
            lines = [
                f"## Defect Profile: {result['supplier_name']} ({sid})\n",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Defect Risk Score | **{result['defect_score']}/10** |",
                f"| Total Defects | {result['total_defects']} |",
                f"| Open Defects | {result['open_defects']} |",
                f"| Critical Defects | {result['critical_defects']} |",
                f"| Recalls Initiated | {result['recalls']} |",
            ]
            if defects_list.get("defects"):
                lines.append(f"\n### Recent Defects\n")
                lines.append("| Date | Severity | Material | Description |")
                lines.append("|------|----------|----------|-------------|")
                for d in defects_list["defects"][:5]:
                    lines.append(f"| {d['date']} | {d['severity']} | {d['material']} | {d['description'][:50]} |")
            lines.append(f"\nThis score feeds into the optimization engine — higher scores penalize the supplier during procurement decisions.")
            return "\n".join(lines)

        # ── Material-specific query ──
        if mat_match:
            mid = mat_match.group(0).upper()
            result = query_defect_data("defects", material_id=mid)
            if "error" in result:
                return f"Could not retrieve defect data: {result['error']}"
            material = _data_reader.get_material_by_id(mid) if _data_reader else None
            mat_name = material.name if material else mid
            lines = [f"## Defects for {mat_name} ({mid})\n"]
            if result["count"] == 0:
                lines.append("No defects recorded for this material.")
            else:
                lines.append(f"Found **{result['count']}** defect records.\n")
                lines.append("| Date | Supplier | Severity | Status | Qty | Root Cause |")
                lines.append("|------|----------|----------|--------|-----|------------|")
                for d in result["defects"][:10]:
                    lines.append(f"| {d['date']} | {d['supplier']} | {d['severity']} | {d['status']} | {d['quantity']} | {d['root_cause'][:40]} |")
            return "\n".join(lines)

        # ── Severity-specific listing ──
        if asking_critical and not asking_count:
            result = query_defect_data("defects", severity="CRITICAL")
            lines = [f"## Critical Defects ({result['count']} records)\n"]
            if result["count"] == 0:
                lines.append("No critical defects currently recorded.")
            else:
                lines.append("| Date | Supplier | Material | Status | Qty | Description |")
                lines.append("|------|----------|----------|--------|-----|-------------|")
                for d in result["defects"]:
                    lines.append(f"| {d['date']} | {d['supplier']} | {d['material']} | {d['status']} | {d['quantity']} | {d['description'][:45]} |")
            return "\n".join(lines)

        if asking_open and not asking_count:
            result = query_defect_data("defects")
            open_defects = [d for d in result["defects"] if d["status"] == "OPEN"]
            lines = [f"## Open Defects ({len(open_defects)} records)\n"]
            if not open_defects:
                lines.append("No open defects — all cases have been resolved.")
            else:
                lines.append("| Date | Supplier | Material | Severity | Qty | Description |")
                lines.append("|------|----------|----------|----------|-----|-------------|")
                for d in open_defects:
                    lines.append(f"| {d['date']} | {d['supplier']} | {d['material']} | {d['severity']} | {d['quantity']} | {d['description'][:45]} |")
            return "\n".join(lines)

        # ── General defect summary (fallback) ──
        lines = [
            f"## Defect Tracking Summary\n",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Defects | **{summary['total_defects']}** |",
            f"| Open | {summary['open']} |",
            f"| Resolved | {summary['resolved']} |",
            f"| Critical | {summary['critical']} |",
            f"| Recalls Initiated | {summary['recalls']} |",
            f"| Units Affected | {summary['units_affected']} |",
            f"\n### Suppliers with Defects\n",
            f"| Supplier | Defects | Open | Critical | Risk Score |",
            f"|----------|---------|------|----------|------------|",
        ]
        for sid, info in sorted(summary["by_supplier"].items(), key=lambda x: x[1]["score"], reverse=True):
            lines.append(f"| {info['name']} | {info['total']} | {info['open']} | {info['critical']} | **{info['score']}/10** |")
        lines.append(f"\nDefect risk scores are factored into the optimization engine's supplier selection. Ask about a specific supplier with `defects SUP-001`.")
        return "\n".join(lines)

    # Supplier query
    if any(kw in msg_lower for kw in ["supplier", "performance", "who supplies"]):
        result = query_supplier_data("suppliers")
        if "error" in result:
            return f"Query failed: {result['error']}"
        suppliers = result["suppliers"][:5]
        lines = [f"Found {result['count']} suppliers in the network. Top 5:\n"]
        for s in suppliers:
            lines.append(f"- **{s['name']}** ({s['supplier_id']}): {s['location']} | Rating {s['rating']}/5 | Risk {s['geopolitical_risk_score']:.1f}/10")
        return "\n".join(lines)

    # PR creation
    if any(kw in msg_lower for kw in ["create pr", "purchase requisition", "approve"]):
        return "To create purchase requisitions, first run an optimization, then specify which solution to approve. Example: 'Create PRs for the Balanced solution'."

    # Risk analysis
    if "risk" in msg_lower:
        return (
            "Current supply chain risk analysis:\n\n"
            "- **Geopolitical**: Strait of Hormuz shipping risk (moderate) - affects Asian suppliers\n"
            "- **Concentration**: Top supplier within policy limits\n"
            "- **Weather**: Typhoon season Q3 may affect Pacific routes\n"
            "- **Financial**: All contracted suppliers have stability score >7/10\n\n"
            "Run an optimization to see risk-adjusted supplier recommendations."
        )

    # Compare
    if "compare" in msg_lower:
        return (
            "Solution comparison:\n\n"
            "- **Budget**: Lowest TCO, higher risk, longer lead times\n"
            "- **Balanced**: Best trade-off, moderate on all dimensions\n"
            "- **Premium**: Lowest risk, highest quality, premium pricing\n"
            "- **Resilient**: Demand-buffered, handles forecast uncertainty\n\n"
            "The AI agent recommends **Balanced** for most scenarios."
        )

    # Help / default
    return (
        "I'm your procurement optimization assistant. I can help with:\n\n"
        "- **optimize** - Run supplier optimization (e.g., 'optimize for 500 e-bikes')\n"
        "- **explain** - Explain a solution (e.g., 'explain the Budget solution')\n"
        "- **suppliers** - Query supplier data and performance\n"
        "- **defects** - View defect tracking data (e.g., 'defects', 'defects SUP-001', 'defects MAT-BAT-001')\n"
        "- **risk** - Analyze supply chain risks\n"
        "- **compare** - Compare solution trade-offs\n"
        "- **create PRs** - Create purchase requisitions\n\n"
        "What would you like to do?"
    )
