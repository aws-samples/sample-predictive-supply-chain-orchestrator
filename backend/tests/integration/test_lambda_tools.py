"""
Integration tests for Lambda tools.

These Lambdas are AgentCore Gateway MCP targets: on success they return a
raw dict (the Gateway serializes it directly as the tool result), and on
failure they raise (the Gateway marks the tool call as failed). Tests assert
that contract — not an API Gateway proxy envelope.

Path setup is handled by tests/integration/conftest.py.
"""

import os

import pytest
from unittest.mock import Mock, patch

from aws.lambda_tools import optimization_tool, explainability_tool, data_access_tool

_LAMBDA_DATA_DIR = "/opt/data"
_NEPTUNE_ENDPOINT = os.environ.get("NEPTUNE_ENDPOINT", "")
_skip_no_lambda_data = pytest.mark.skipif(
    not os.path.isdir(_LAMBDA_DATA_DIR),
    reason=f"Lambda data directory {_LAMBDA_DATA_DIR} not available (local dev)"
)
_skip_no_neptune = pytest.mark.skipif(
    not _NEPTUNE_ENDPOINT,
    reason="NEPTUNE_ENDPOINT not set (local dev)"
)


class TestOptimizationTool:
    """Test suite for optimization Lambda tool."""

    @pytest.mark.integration
    @_skip_no_lambda_data
    def test_lambda_handler_success(self):
        """Successful optimization returns a raw dict with solutions."""
        event = {
            "materials": [{"material_id": "MAT-001", "quantity": 100}],
            "constraints": {
                "max_supplier_concentration": 0.40,
                "max_lead_time_days": 45,
                "budget_max": 1000000,
            },
            "objectives": {"cost": 0.4, "risk": 0.3, "lead_time": 0.3},
        }
        context = Mock()
        context.aws_request_id = "test-request-123"

        result = optimization_tool.lambda_handler(event, context)

        assert "solutions" in result
        assert len(result["solutions"]) > 0
        assert result["request_id"] == "test-request-123"

    def test_lambda_handler_empty_materials(self):
        """Empty materials raises ValueError (Gateway marks tool failed)."""
        event = {"materials": [], "constraints": {}, "objectives": {}}
        context = Mock()
        context.aws_request_id = "test-request-123"

        with pytest.raises(ValueError, match="materials"):
            optimization_tool.lambda_handler(event, context)

    def test_lambda_handler_missing_materials(self):
        """Missing materials key raises ValueError."""
        event = {"constraints": {}, "objectives": {}}
        context = Mock()
        context.aws_request_id = "test-request-123"

        with pytest.raises(ValueError):
            optimization_tool.lambda_handler(event, context)

    @_skip_no_lambda_data
    def test_lambda_handler_exception(self):
        """Unexpected errors during optimization propagate to the Gateway."""
        event = {"materials": [{"material_id": "MAT-001", "quantity": 100}]}
        context = Mock()
        context.aws_request_id = "test-request-123"

        with patch.object(
            optimization_tool.OptimizationEngine, "optimize",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with pytest.raises(RuntimeError):
                optimization_tool.lambda_handler(event, context)


class TestExplainabilityTool:
    """Test suite for explainability Lambda tool."""

    def test_lambda_handler_cost_optimized_solution(self):
        """Cost-Optimized (engine name) returns a cost-minimization explanation."""
        event = {
            "solution_name": "Cost-Optimized",
            "total_cost": 650000,
            "risk_score": 7.5,
            "quality_score": 6.5,
            "allocations": [
                {"supplier_id": "SUP-001", "material_id": "MAT-001", "quantity": 100}
            ],
        }
        context = Mock()
        context.aws_request_id = "test-request-123"

        result = explainability_tool.lambda_handler(event, context)

        assert "explanation" in result
        assert "Cost-Optimized" in result["explanation"]
        assert "cost minimization" in result["explanation"].lower()

    def test_lambda_handler_balanced_solution(self):
        event = {
            "solution_name": "Balanced",
            "total_cost": 875000,
            "risk_score": 3.5,
            "quality_score": 8.2,
            "allocations": [{"supplier_id": "SUP-001"}, {"supplier_id": "SUP-002"}],
        }
        context = Mock()
        context.aws_request_id = "test-request-123"

        result = explainability_tool.lambda_handler(event, context)

        assert "Balanced" in result["explanation"]
        assert "optimal balance" in result["explanation"].lower()

    def test_lambda_handler_risk_diversified_solution(self):
        """Risk-Diversified (engine name) returns a quality/risk explanation."""
        event = {
            "solution_name": "Risk-Diversified",
            "total_cost": 1200000,
            "risk_score": 1.5,
            "quality_score": 9.5,
            "allocations": [{"supplier_id": "SUP-003"}],
        }
        context = Mock()
        context.aws_request_id = "test-request-123"

        result = explainability_tool.lambda_handler(event, context)

        assert "Risk-Diversified" in result["explanation"]
        assert "quality" in result["explanation"].lower()

    def test_lambda_handler_missing_solution_name(self):
        """Missing solution_name raises ValueError."""
        event = {
            "total_cost": 100000,
            "risk_score": 5.0,
            "quality_score": 7.0,
            "allocations": [],
        }
        context = Mock()
        context.aws_request_id = "test-request-123"

        with pytest.raises(ValueError):
            explainability_tool.lambda_handler(event, context)

    def test_generate_explanation_with_diversification(self):
        explanation = explainability_tool._generate_explanation(
            "Balanced", 875000, 3.5, 8.2,
            [{"supplier_id": "SUP-001"}, {"supplier_id": "SUP-002"}],
        )
        assert "diversification" in explanation.lower()
        assert "2 supplier" in explanation

    def test_legacy_alias_budget_maps_to_cost(self):
        """Legacy 'Budget' alias still yields the cost-minimization explanation."""
        explanation = explainability_tool._generate_explanation(
            "Budget", 650000, 7.5, 6.5, [{"supplier_id": "SUP-001"}],
        )
        assert "cost minimization" in explanation.lower()


class TestDataAccessTool:
    """Test suite for data access Lambda tool."""

    @_skip_no_neptune
    def test_lambda_handler_find_alternative_suppliers(self):
        event = {
            "query_type": "find_alternative_suppliers",
            "material_id": "MAT-001",
            "max_hops": 2,
        }
        context = Mock()
        context.aws_request_id = "test-request-123"

        result = data_access_tool.lambda_handler(event, context)

        assert "material_id" in result
        assert "alternative_suppliers" in result

    @_skip_no_neptune
    def test_lambda_handler_get_supplier_details(self):
        event = {"query_type": "get_supplier_details", "supplier_id": "SUP-001"}
        context = Mock()
        context.aws_request_id = "test-request-123"

        result = data_access_tool.lambda_handler(event, context)

        assert "supplier_id" in result

    def test_lambda_handler_removed_query_type(self):
        """A removed/unknown query type raises ValueError."""
        event = {"query_type": "get_material_specifications", "material_id": "MAT-001"}
        context = Mock()
        context.aws_request_id = "test-request-123"

        with pytest.raises(ValueError):
            data_access_tool.lambda_handler(event, context)

    def test_lambda_handler_missing_query_type(self):
        event = {"material_id": "MAT-001"}
        context = Mock()
        context.aws_request_id = "test-request-123"

        with pytest.raises(ValueError):
            data_access_tool.lambda_handler(event, context)

    def test_lambda_handler_unknown_query_type(self):
        event = {"query_type": "unknown_query", "material_id": "MAT-001"}
        context = Mock()
        context.aws_request_id = "test-request-123"

        with pytest.raises(ValueError, match="query_type"):
            data_access_tool.lambda_handler(event, context)
