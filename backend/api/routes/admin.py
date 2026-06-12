"""Admin blueprint — AgentCore Gateway, Memory, Policies, Neptune reload."""

import json
import os
import re
from datetime import datetime

import boto3
import structlog
from flask import Blueprint, jsonify, request

try:
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    ClientError = Exception
    BotoCoreError = Exception

logger = structlog.get_logger()

admin_bp = Blueprint("admin", __name__)

# ---------------------------------------------------------------------------
# Module-level constants & helpers
# ---------------------------------------------------------------------------
AGENTCORE_GATEWAY_ID = os.environ.get("AGENTCORE_GATEWAY_ID", "")
AGENTCORE_MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
AGENTCORE_POLICY_ENGINE_ID = os.environ.get("AGENTCORE_POLICY_ENGINE_ID", "")


def _get_agentcore_control():
    return boto3.client(
        "bedrock-agentcore-control",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )


def _get_agentcore_data():
    return boto3.client(
        "bedrock-agentcore",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )


# ---------------------------------------------------------------------------
# 1. POST /api/admin/reload-neptune
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/reload-neptune", methods=["POST"])
def reload_neptune():
    """Trigger Neptune bulk loader to reload data from S3."""
    try:
        from api.state import neptune_client

        if not neptune_client:
            return jsonify({"error": "Neptune not connected"}), 400

        # Update supplier names via Gremlin property updates instead of bulk loader
        new_names = {
            "SUP-001": "Shenzhen LiPower Energy Co.",
            "SUP-002": "Samsung SDI (Korea)",
            "SUP-003": "Panasonic Energy (San Jose)",
            "SUP-004": "Bafang Electric (Suzhou)",
            "SUP-005": "Shimano Components (Taipei)",
            "SUP-006": "Bosch eBike Systems",
            "SUP-007": "Giant Manufacturing Co.",
            "SUP-008": "Merida Industry Co.",
            "SUP-009": "Reynolds Technology (UK)",
            "SUP-010": "Garmin Display Systems",
            "SUP-011": "Continental Electronics",
            "SUP-012": "Sigma Sport (Germany)",
            "SUP-013": "DT Swiss AG",
            "SUP-014": "Mavic SAS (France)",
            "SUP-015": "SRAM Corporation",
        }

        updated = 0
        for sid, name in new_names.items():
            if not re.match(r"^SUP-\d{3}$", sid):
                continue
            safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
            try:
                neptune_client._http_query(
                    f"g.V('{sid}').property(single, 'name', '{safe_name}')"
                )
                updated += 1
            except (ClientError, BotoCoreError, ConnectionError) as e:
                logger.warning(
                    "neptune_name_update_failed", supplier_id=sid, error=str(e)
                )

        return (
            jsonify(
                {"status": "updated", "updated": updated, "total": len(new_names)}
            ),
            200,
        )

    except (ClientError, BotoCoreError, ConnectionError) as e:
        logger.error("neptune_reload_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# 2. GET /api/admin/gateway
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/gateway", methods=["GET"])
def admin_gateway():
    """Get AgentCore Gateway status and targets."""
    try:
        ctrl = _get_agentcore_control()
        gw = ctrl.get_gateway(gatewayIdentifier=AGENTCORE_GATEWAY_ID)
        targets_resp = ctrl.list_gateway_targets(
            gatewayIdentifier=AGENTCORE_GATEWAY_ID
        )
        targets = targets_resp.get("items", [])

        return jsonify(
            {
                "gateway_id": gw.get("gatewayId", AGENTCORE_GATEWAY_ID),
                "name": gw.get("name", ""),
                "protocol": gw.get("protocolType", "MCP"),
                "auth_type": gw.get("authorizerType", "AWS_IAM"),
                "status": gw.get("status", "UNKNOWN"),
                "policy_engine": gw.get("policyEngineConfiguration", {}),
                "tools": [
                    {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "target_name": t.get("name", ""),
                        "status": t.get("status", "UNKNOWN").lower(),
                        "target_id": t.get("targetId", ""),
                    }
                    for t in targets
                ],
            }
        )
    except (ClientError, BotoCoreError, ConnectionError) as e:
        logger.error("admin_gateway_error", error=str(e))
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Helper — extract readable turn content from AgentCore conversation payload
# ---------------------------------------------------------------------------
def _extract_turn_content(conv):
    """Extract readable text and tools from an AgentCore conversational payload.

    The payload may be simple ``{role, content: {text}}`` or the full Bedrock
    message format ``{message: {role, content: [{text: ...}, {toolUse: ...}]}}``.
    """
    tools_used = []

    # Try nested message format first: {message: {role, content: [...]}}
    msg = conv.get("message", conv)
    role = msg.get("role", conv.get("role", "OTHER")).lower()
    raw_content = msg.get("content", conv.get("content", ""))

    # content can be a list of blocks [{text: ...}, {toolUse: ...}, {toolResult: ...}]
    if isinstance(raw_content, list):
        text_parts = []
        for block in raw_content:
            if isinstance(block, dict):
                if "text" in block:
                    text_parts.append(block["text"])
                elif "toolUse" in block:
                    tool_name = block["toolUse"].get("name", "tool")
                    tools_used.append(tool_name)
                elif "toolResult" in block:
                    # Skip tool results — they're verbose JSON
                    continue
            elif isinstance(block, str):
                text_parts.append(block)
        text = "\n".join(text_parts) if text_parts else ""
    elif isinstance(raw_content, dict):
        text = raw_content.get("text", "")
    elif isinstance(raw_content, str):
        text = raw_content
    else:
        text = str(raw_content) if raw_content else ""

    # If we still have JSON-looking content, try to extract text from it
    if text.startswith('{"message"'):
        try:
            parsed = json.loads(text)
            return _extract_turn_content(parsed)
        except (json.JSONDecodeError, RecursionError):
            pass

    # Skip turns that are only tool results with no text
    if not text and not tools_used:
        return None

    return {"role": role, "content": text, "tools_used": tools_used}


# ---------------------------------------------------------------------------
# 3. GET /api/admin/memory/sessions
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/memory/sessions", methods=["GET"])
def admin_memory_sessions():
    """List recent memory events (conversation turns stored in AgentCore Memory)."""
    try:
        data = _get_agentcore_data()
        actor_id = request.args.get("actor_id", "demo-user")

        # List sessions for this actor — fetch all, sort by recency, take top 10
        sessions = []
        try:
            resp = data.list_sessions(
                memoryId=AGENTCORE_MEMORY_ID, actorId=actor_id, maxResults=50
            )
            raw_sessions = resp.get(
                "sessionSummaries", resp.get("sessions", resp.get("items", []))
            )
            # Sort by creation time descending (newest first) then take top 10
            raw_sessions.sort(
                key=lambda s: s.get("createdAt", ""), reverse=True
            )
            raw_sessions = raw_sessions[:10]
            for s in raw_sessions:
                sid = s.get("sessionId", "")
                # Get events for this session
                try:
                    events_resp = data.list_events(
                        memoryId=AGENTCORE_MEMORY_ID,
                        actorId=actor_id,
                        sessionId=sid,
                    )
                    events = events_resp.get("events", [])
                    for ev in events:
                        for payload_item in ev.get("payload", []):
                            conv = payload_item.get("conversational", {})
                            if not conv:
                                continue
                            turn = _extract_turn_content(conv)
                            if turn is None:
                                continue
                            sessions.append(
                                {
                                    "session_id": sid,
                                    "turn_id": len(sessions),
                                    "user_id": ev.get("actorId", actor_id),
                                    "role": turn["role"],
                                    "content": turn["content"],
                                    "tools_used": turn["tools_used"],
                                    "created_at": (
                                        int(
                                            datetime.fromisoformat(
                                                str(
                                                    ev.get("eventTimestamp", "")
                                                ).replace("Z", "+00:00")
                                            ).timestamp()
                                        )
                                        if ev.get("eventTimestamp")
                                        else 0
                                    ),
                                }
                            )
                except Exception:  # Intentional skip for malformed session events
                    pass
        except AttributeError:
            # list_sessions not available — try listing events directly for known sessions
            pass

        if not sessions:
            # Fallback: try known actor sessions directly
            for sid in ["llm-live-001", "web-5d4bb65f", "web-95f38920"]:
                try:
                    events_resp = data.list_events(
                        memoryId=AGENTCORE_MEMORY_ID,
                        actorId=actor_id,
                        sessionId=sid,
                    )
                    for ev in events_resp.get("events", []):
                        for payload_item in ev.get("payload", []):
                            conv = payload_item.get("conversational", {})
                            if not conv:
                                continue
                            turn = _extract_turn_content(conv)
                            if turn is None:
                                continue
                            sessions.append(
                                {
                                    "session_id": sid,
                                    "turn_id": len(sessions),
                                    "user_id": ev.get("actorId", actor_id),
                                    "role": turn["role"],
                                    "content": turn["content"],
                                    "tools_used": turn["tools_used"],
                                    "created_at": 0,
                                }
                            )
                except Exception:  # Intentional skip for malformed/missing sessions
                    continue

        return jsonify(sessions)
    except Exception as e:  # Broad catch: admin endpoint with multiple AWS service calls
        logger.error("admin_memory_sessions_error", error=str(e))
        return jsonify([])


# ---------------------------------------------------------------------------
# 4. GET /api/admin/memory/entries
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/memory/entries", methods=["GET"])
def admin_memory_entries():
    """List long-term memory entries."""
    try:
        ctrl = _get_agentcore_control()
        memory = ctrl.get_memory(memoryId=AGENTCORE_MEMORY_ID)
        mem = memory.get("memory", {})

        strategies = mem.get("strategies", [])
        return jsonify(
            {
                "memory_id": mem.get("id", AGENTCORE_MEMORY_ID),
                "name": mem.get("name", ""),
                "status": mem.get("status", ""),
                "event_expiry_days": mem.get("eventExpiryDuration", 0),
                "strategies": [
                    {
                        "strategy_id": s.get("strategyId", ""),
                        "name": s.get("name", ""),
                        "type": s.get("type", ""),
                        "status": s.get("status", ""),
                        "namespaces": s.get("namespaces", []),
                    }
                    for s in strategies
                ],
                "records": [],  # Will populate when events are sent
            }
        )
    except (ClientError, BotoCoreError, ConnectionError) as e:
        logger.error("admin_memory_entries_error", error=str(e))
        return jsonify(
            {
                "memory_id": AGENTCORE_MEMORY_ID,
                "strategies": [],
                "records": [],
                "error": str(e),
            }
        )


# ---------------------------------------------------------------------------
# 5. GET /api/admin/memory/records
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/memory/records", methods=["GET"])
def admin_memory_records():
    """List actual memory records from all strategy namespaces."""
    try:
        data = _get_agentcore_data()
        actor_id = request.args.get("actor_id", "demo-user")
        max_items = int(request.args.get("max_items", "50"))

        # Namespaces per strategy (must match memory_stack.py)
        strategy_namespaces = {
            "SupplierInsights": {
                "namespace": f"{actor_id}/supplier-insights",
                "type": "SEMANTIC",
                "description": "Supplier facts and insights extracted from conversations",
            },
            "UserPreferences": {
                "namespace": f"{actor_id}/preferences",
                "type": "USER_PREFERENCE",
                "description": "Optimization preferences, budget constraints, strategy choices",
            },
        }

        all_records = []
        for strategy_name, info in strategy_namespaces.items():
            try:
                resp = data.list_memory_records(
                    memoryId=AGENTCORE_MEMORY_ID,
                    namespace=info["namespace"],
                    maxResults=max_items,
                )
                raw_records = resp.get(
                    "memoryRecordSummaries", resp.get("records", [])
                )
                for rec in raw_records:
                    # Extract readable content from the record
                    content = rec.get("content", rec.get("value", ""))
                    if isinstance(content, dict):
                        content = content.get("text", json.dumps(content))
                    all_records.append(
                        {
                            "record_id": rec.get(
                                "memoryRecordId", rec.get("id", "")
                            ),
                            "strategy": strategy_name,
                            "strategy_type": info["type"],
                            "namespace": info["namespace"],
                            "content": str(content),
                            "created_at": rec.get(
                                "createdAt", rec.get("created_at", "")
                            ),
                            "updated_at": rec.get(
                                "updatedAt", rec.get("updated_at", "")
                            ),
                            "score": rec.get("score", None),
                        }
                    )
            except (ClientError, BotoCoreError, ConnectionError) as e:
                logger.warning(
                    "memory_records_list_error",
                    strategy=strategy_name,
                    error=str(e),
                )

        return jsonify({"records": all_records, "actor_id": actor_id})
    except (ClientError, BotoCoreError, ConnectionError) as e:
        logger.error("admin_memory_records_error", error=str(e))
        return jsonify({"records": [], "error": str(e)})


# ---------------------------------------------------------------------------
# 6. GET /api/admin/memory/search
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/memory/search", methods=["GET"])
def admin_memory_search():
    """Semantic search across long-term memory records."""
    try:
        data = _get_agentcore_data()
        query = request.args.get("q", "")
        actor_id = request.args.get("actor_id", "demo-user")
        max_items = int(request.args.get("max_items", "10"))

        if not query:
            return (
                jsonify(
                    {"records": [], "error": "Missing query parameter 'q'"}
                ),
                400,
            )

        # Search across both semantic namespaces
        search_namespaces = [
            {
                "namespace": f"{actor_id}/supplier-insights",
                "strategy": "SupplierInsights",
                "type": "SEMANTIC",
            },
            {
                "namespace": f"{actor_id}/preferences",
                "strategy": "UserPreferences",
                "type": "USER_PREFERENCE",
            },
        ]

        all_results = []
        for ns in search_namespaces:
            try:
                resp = data.retrieve_memory_records(
                    memoryId=AGENTCORE_MEMORY_ID,
                    namespace=ns["namespace"],
                    searchCriteria={"searchQuery": query},
                    maxResults=max_items,
                )
                raw_records = resp.get(
                    "memoryRecordSummaries", resp.get("records", [])
                )
                for rec in raw_records:
                    content = rec.get("content", rec.get("value", ""))
                    if isinstance(content, dict):
                        content = content.get("text", json.dumps(content))
                    all_results.append(
                        {
                            "record_id": rec.get(
                                "memoryRecordId", rec.get("id", "")
                            ),
                            "strategy": ns["strategy"],
                            "strategy_type": ns["type"],
                            "namespace": ns["namespace"],
                            "content": str(content),
                            "score": rec.get("score", None),
                            "created_at": rec.get(
                                "createdAt", rec.get("created_at", "")
                            ),
                            "updated_at": rec.get(
                                "updatedAt", rec.get("updated_at", "")
                            ),
                        }
                    )
            except (ClientError, BotoCoreError, ConnectionError) as e:
                logger.warning(
                    "memory_search_error",
                    namespace=ns["namespace"],
                    error=str(e),
                )

        # Sort by relevance score descending
        all_results.sort(key=lambda r: r.get("score") or 0, reverse=True)

        return jsonify(
            {"records": all_results, "query": query, "actor_id": actor_id}
        )
    except (ClientError, BotoCoreError, ConnectionError) as e:
        logger.error("admin_memory_search_error", error=str(e))
        return jsonify({"records": [], "error": str(e)})


# ---------------------------------------------------------------------------
# 7. GET /api/admin/policies
# ---------------------------------------------------------------------------
@admin_bp.route("/api/admin/policies", methods=["GET"])
def admin_policies():
    """List Cedar policies from the PolicyEngine."""
    roles = [
        {
            "name": "Analyst",
            "description": "Read-only access to supplier data and explanations",
            "allowed_tools": ["query_supplier_data", "explain_solution"],
            "allowed_actions": ["ReadData"],
            "max_budget_authority": 0,
        },
        {
            "name": "ProcurementManager",
            "description": "Full optimization, data access, and PR creation",
            "allowed_tools": [
                "optimize_suppliers",
                "query_supplier_data",
                "explain_solution",
                "create_purchase_requisitions",
            ],
            "allowed_actions": ["InvokeTool", "ReadData", "CreatePR"],
            "max_budget_authority": 5_000_000,
        },
        {
            "name": "Admin",
            "description": "Unrestricted access to all tools",
            "allowed_tools": ["*"],
            "allowed_actions": ["*"],
            "max_budget_authority": 10_000_000,
        },
    ]
    try:
        ctrl = _get_agentcore_control()
        # Try control plane APIs (may not be available in Lambda's boto3 version)
        try:
            engine = ctrl.get_policy_engine(
                policyEngineId=AGENTCORE_POLICY_ENGINE_ID
            )
            policies_resp = ctrl.list_policies(
                policyEngineId=AGENTCORE_POLICY_ENGINE_ID
            )
            policies = policies_resp.get(
                "policies", policies_resp.get("items", [])
            )
            policy_list = []
            for p in policies:
                try:
                    detail = ctrl.get_policy(
                        policyEngineId=AGENTCORE_POLICY_ENGINE_ID,
                        policyId=p.get("policyId", ""),
                    )
                    cedar_def = detail.get("definition", {}).get("cedar", {})
                    policy_list.append(
                        {
                            "name": p.get("name", detail.get("name", "")),
                            "description": detail.get("description", ""),
                            "statement": cedar_def.get("statement", ""),
                            "effect": (
                                "forbid"
                                if "forbid" in cedar_def.get("statement", "")
                                else "permit"
                            ),
                            "status": p.get(
                                "status", detail.get("status", "")
                            ),
                        }
                    )
                except (ClientError, BotoCoreError, ConnectionError):
                    policy_list.append(
                        {
                            "name": p.get("name", ""),
                            "status": p.get("status", ""),
                        }
                    )
            return jsonify(
                {
                    "policy_engine_id": engine.get(
                        "policyEngineId", AGENTCORE_POLICY_ENGINE_ID
                    ),
                    "policy_engine_status": engine.get("status", ""),
                    "mode": "LOG_ONLY",
                    "policies": policy_list,
                    "roles": roles,
                }
            )
        except AttributeError:
            # boto3 version too old — return known metadata
            return jsonify(
                {
                    "policy_engine_id": AGENTCORE_POLICY_ENGINE_ID,
                    "policy_engine_status": "ACTIVE",
                    "mode": "LOG_ONLY",
                    "policies": [
                        {
                            "name": "AnalystReadData",
                            "description": "Analyst: read-only data queries",
                            "statement": 'permit (principal, action == Action::"ToolCall", resource == Tool::"query-supplier-data::query_supplier_data") when { principal has role && principal.role == "Analyst" };',
                            "effect": "permit",
                            "role": "Analyst",
                        },
                        {
                            "name": "AnalystExplain",
                            "description": "Analyst: view explanations",
                            "statement": 'permit (principal, action == Action::"ToolCall", resource == Tool::"explain-solution::explain_solution") when { principal has role && principal.role == "Analyst" };',
                            "effect": "permit",
                            "role": "Analyst",
                        },
                        {
                            "name": "ManagerOptimize",
                            "description": "Manager: run optimization",
                            "statement": 'permit (principal, action == Action::"ToolCall", resource == Tool::"optimize-suppliers::optimize_suppliers") when { principal has role && principal.role == "ProcurementManager" };',
                            "effect": "permit",
                            "role": "ProcurementManager",
                        },
                        {
                            "name": "ManagerDataAccess",
                            "description": "Manager: query data",
                            "statement": 'permit (principal, action == Action::"ToolCall", resource == Tool::"query-supplier-data::query_supplier_data") when { principal has role && principal.role == "ProcurementManager" };',
                            "effect": "permit",
                            "role": "ProcurementManager",
                        },
                        {
                            "name": "AdminFullAccess",
                            "description": "Admin: unrestricted",
                            "statement": 'permit (principal, action, resource) when { principal has role && principal.role == "Admin" };',
                            "effect": "permit",
                            "role": "Admin",
                        },
                        {
                            "name": "DenyExcessiveBudget",
                            "description": "Guardrail: block >$10M budget",
                            "statement": 'forbid (principal, action == Action::"ToolCall", resource == Tool::"optimize-suppliers::optimize_suppliers") when { context has budget_max && context.budget_max > 10000000 };',
                            "effect": "forbid",
                        },
                    ],
                    "roles": roles,
                }
            )
    except Exception as e:  # Broad catch: admin endpoint with multiple AWS service calls
        logger.error("admin_policies_error", error=str(e))
        return jsonify({"policies": [], "roles": roles, "error": str(e)})
