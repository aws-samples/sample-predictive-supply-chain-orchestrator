"""
MCP tool definitions for AgentCore Gateway.

Defines JSON Schema-based tool specifications for each Lambda tool,
following the Model Context Protocol (MCP) standard.
"""

OPTIMIZATION_TOOL = {
    "name": "optimize_suppliers",
    "description": (
        "Run multi-objective supplier optimization for e-bike manufacturing materials. "
        "Returns a Pareto frontier of solutions (Cost-Optimized, Balanced, Risk-Diversified) "
        "with supplier allocations, costs, risk scores, and quality metrics. "
        "Supports constraints on supplier concentration, lead time, and budget."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "materials": {
                "type": "array",
                "description": "List of materials to optimize procurement for",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {
                            "type": "string",
                            "description": "Material identifier (e.g. MAT-BAT-001)",
                            "pattern": "^MAT-[A-Z]{3}-\\d{3}$"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Required quantity to procure",
                            "minimum": 1,
                            "maximum": 1000000
                        },
                        "required_by": {
                            "type": "string",
                            "description": "Required delivery date in YYYY-MM-DD format",
                            "format": "date"
                        }
                    },
                    "required": ["material_id", "quantity"]
                },
                "minItems": 1,
                "maxItems": 100
            },
            "constraints": {
                "type": "object",
                "description": "Optimization constraints",
                "properties": {
                    "max_supplier_concentration": {
                        "type": "number",
                        "description": "Maximum order share for any single supplier (0.0-1.0)",
                        "minimum": 0.1,
                        "maximum": 1.0,
                        "default": 0.4
                    },
                    "max_lead_time_days": {
                        "type": "integer",
                        "description": "Maximum acceptable lead time in days",
                        "minimum": 1,
                        "maximum": 365,
                        "default": 45
                    },
                    "budget_max": {
                        "type": "number",
                        "description": "Maximum total budget in USD",
                        "minimum": 0
                    },
                    "budget_min": {
                        "type": "number",
                        "description": "Minimum total budget in USD",
                        "minimum": 0
                    },
                    "prefer_contracted_suppliers": {
                        "type": "boolean",
                        "description": "Whether to prefer suppliers with active contracts",
                        "default": True
                    }
                }
            }
        },
        "required": ["materials"]
    },
}

DATA_ACCESS_TOOL = {
    "name": "query_supplier_data",
    "description": (
        "Query the supplier network graph database. Supports finding alternative "
        "suppliers for a material via graph traversal, retrieving a supplier's "
        "network relationships, getting detailed supplier information, and "
        "analyzing sourcing risk (single-sourced, dual-sourced materials)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "description": "Type of query to execute",
                "enum": [
                    "find_alternative_suppliers",
                    "get_supplier_network",
                    "get_supplier_details",
                    "get_sourcing_summary"
                ]
            },
            "material_id": {
                "type": "string",
                "description": "Material identifier (required for find_alternative_suppliers)",
                "pattern": "^MAT-[A-Z]{3}-\\d{3}$"
            },
            "supplier_id": {
                "type": "string",
                "description": "Supplier identifier (required for get_supplier_network and get_supplier_details)",
                "pattern": "^SUP-\\d{3}$"
            },
            "max_hops": {
                "type": "integer",
                "description": "Maximum graph traversal depth for alternative supplier search",
                "minimum": 1,
                "maximum": 5,
                "default": 2
            },
            "depth": {
                "type": "integer",
                "description": "Network depth for supplier network queries",
                "minimum": 1,
                "maximum": 5,
                "default": 2
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "minimum": 1,
                "maximum": 50,
                "default": 10
            }
        },
        "required": ["query_type"]
    },
}

EXPLAINABILITY_TOOL = {
    "name": "explain_solution",
    "description": (
        "Generate a human-readable business explanation for an optimization solution. "
        "Explains why a particular supplier mix was chosen, including cost trade-offs, "
        "risk analysis, quality considerations, and TCO breakdown."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "solution_name": {
                "type": "string",
                "description": "Name of the optimization solution to explain",
                "enum": ["Cost-Optimized", "Balanced", "Risk-Diversified", "Custom"]
            },
            "total_cost": {
                "type": "number",
                "description": "Total cost of the solution in USD",
                "minimum": 0
            },
            "risk_score": {
                "type": "number",
                "description": "Risk score of the solution (0-10 scale)",
                "minimum": 0,
                "maximum": 10
            },
            "quality_score": {
                "type": "number",
                "description": "Quality score of the solution (0-10 scale)",
                "minimum": 0,
                "maximum": 10
            },
            "allocations": {
                "type": "array",
                "description": "Supplier allocations in the solution",
                "items": {
                    "type": "object",
                    "properties": {
                        "supplier_id": {"type": "string"},
                        "supplier_name": {"type": "string"},
                        "material_id": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "unit_price": {"type": "number"},
                        "total_cost": {"type": "number"},
                        "lead_time_days": {"type": "integer"},
                        "quality_score": {"type": "number"},
                        "freight_cost": {"type": "number"},
                        "carrying_cost": {"type": "number"},
                        "carbon_cost": {"type": "number"},
                        "tco": {"type": "number"}
                    }
                }
            }
        },
        "required": ["solution_name"]
    },
}

# All tools for gateway registration
ALL_TOOLS = [OPTIMIZATION_TOOL, DATA_ACCESS_TOOL, EXPLAINABILITY_TOOL]

# Mapping from MCP tool name to Lambda handler module
TOOL_LAMBDA_MAPPING = {
    "optimize_suppliers": "optimization_tool",
    "query_supplier_data": "data_access_tool",
    "explain_solution": "explainability_tool",
}
