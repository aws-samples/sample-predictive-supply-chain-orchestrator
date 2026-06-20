"""
Unit tests for procurement agent tools.
"""

import pytest
from agents.procurement_agent import (
    optimize_suppliers,
    explain_solution,
    query_supplier_data,
    create_purchase_requisitions,
    get_purchase_requisitions,
    invoke_agent,
    _pr_store,
)


class TestOptimizeSuppliers:

    def test_optimize_basic(self):
        result = optimize_suppliers(
            materials=[{"material_id": "MAT-BAT-001", "quantity": 500}],
            constraints={"max_supplier_concentration": 0.60, "max_lead_time_days": 60, "budget_max": 2000000},
        )
        assert "solutions" in result
        assert result["solutions_count"] >= 3
        for sol in result["solutions"]:
            assert sol["total_cost"] > 0
            assert sol["name"] in ["Cost-Optimized", "Balanced", "Risk-Diversified"]

    def test_optimize_empty_materials(self):
        result = optimize_suppliers(materials=[], constraints={})
        assert "error" in result

    def test_optimize_default_constraints(self):
        result = optimize_suppliers(
            materials=[{"material_id": "MAT-BAT-001", "quantity": 500}],
            constraints={},
        )
        assert "solutions" in result


class TestExplainSolution:

    def test_explain_budget(self):
        result = explain_solution("Budget", 650000, 7.5)
        assert result["solution_name"] == "Budget"
        assert "strategy" in result
        assert "description" in result
        assert "$650,000" in result["description"]

    def test_explain_balanced(self):
        result = explain_solution("Balanced", 875000, 3.5)
        assert "trade-off" in result["strategy"].lower() or "optimal" in result["strategy"].lower()

    def test_explain_premium(self):
        result = explain_solution("Premium", 1200000, 1.5)
        assert "quality" in result["strategy"].lower() or "risk" in result["strategy"].lower()

    def test_explain_resilient_alias(self):
        # "Resilient" is a legacy alias mapped to the current Risk-Diversified strategy.
        result = explain_solution("Resilient", 950000, 2.8)
        assert "quality" in result["strategy"].lower() or "risk" in result["strategy"].lower()

    def test_explain_unknown(self):
        result = explain_solution("Custom", 500000, 5.0)
        assert result["solution_name"] == "Custom"


class TestQuerySupplierData:

    def test_query_suppliers(self):
        result = query_supplier_data("suppliers")
        assert "suppliers" in result
        assert result["count"] > 0

    def test_query_suppliers_by_id(self):
        result = query_supplier_data("suppliers", supplier_id="SUP-001")
        assert result["count"] == 1
        assert result["suppliers"][0]["supplier_id"] == "SUP-001"

    def test_query_materials(self):
        result = query_supplier_data("materials")
        assert "materials" in result
        assert result["count"] > 0

    def test_query_performance(self):
        result = query_supplier_data("performance")
        assert "performance" in result
        assert result["count"] > 0

    def test_query_alternatives(self):
        result = query_supplier_data("alternatives", material_id="MAT-BAT-001")
        assert "alternatives" in result
        assert result["count"] > 0

    def test_query_alternatives_no_material(self):
        result = query_supplier_data("alternatives")
        assert "error" in result

    def test_query_unknown_type(self):
        result = query_supplier_data("unknown")
        assert "error" in result


class TestPurchaseRequisitions:

    def setup_method(self):
        _pr_store.clear()

    def test_create_prs(self):
        result = create_purchase_requisitions(
            "Balanced",
            [
                {"supplier_id": "SUP-001", "material_id": "MAT-BAT-001", "quantity": 500, "unit_price": 280},
                {"supplier_id": "SUP-002", "material_id": "MAT-MOT-001", "quantity": 500, "unit_price": 45},
            ],
        )
        assert result["total_prs"] == 2
        assert result["total_value"] == 500 * 280 + 500 * 45
        assert result["status"] == "pending_approval"
        assert len(result["pr_ids"]) == 2

    def test_get_prs(self):
        create_purchase_requisitions("Budget", [
            {"supplier_id": "SUP-001", "material_id": "MAT-BAT-001", "quantity": 100, "unit_price": 50},
        ])
        result = get_purchase_requisitions()
        assert result["total"] >= 1

    def test_create_prs_same_supplier(self):
        result = create_purchase_requisitions(
            "Premium",
            [
                {"supplier_id": "SUP-001", "material_id": "MAT-BAT-001", "quantity": 200, "unit_price": 100},
                {"supplier_id": "SUP-001", "material_id": "MAT-MOT-001", "quantity": 300, "unit_price": 50},
            ],
        )
        assert result["total_prs"] == 1  # Same supplier grouped


class TestInvokeAgent:

    def test_invoke_help(self):
        response = invoke_agent("help")
        assert "optimization" in response.lower() or "optimize" in response.lower()

    def test_invoke_optimize(self):
        response = invoke_agent("optimize for 500 e-bikes")
        assert "solution" in response.lower() or "optim" in response.lower()

    def test_invoke_explain(self):
        # "Budget" is a legacy alias; the agent explains the Cost-Optimized strategy.
        response = invoke_agent("explain the Budget solution")
        assert "cost-optimized" in response.lower()

    def test_invoke_risk(self):
        response = invoke_agent("risk analysis")
        assert "risk" in response.lower()

    def test_invoke_compare(self):
        response = invoke_agent("compare solutions")
        assert "budget" in response.lower() or "balanced" in response.lower()

    def test_invoke_suppliers(self):
        response = invoke_agent("show supplier data")
        assert "supplier" in response.lower()


# Import the new defect query function
from agents.procurement_agent import query_defect_data


class TestQueryDefectData:
    """Test query_defect_data tool function."""

    def test_summary(self):
        result = query_defect_data("summary")
        assert "total_defects" in result
        assert result["total_defects"] == 20
        assert result["open"] >= 0
        assert result["critical"] >= 0
        assert "by_supplier" in result
        assert len(result["by_supplier"]) > 0

    def test_summary_supplier_scores(self):
        result = query_defect_data("summary")
        for sid, info in result["by_supplier"].items():
            assert "name" in info
            assert "score" in info
            assert 0 <= info["score"] <= 10

    def test_defects_all(self):
        result = query_defect_data("defects")
        assert "defects" in result
        assert result["count"] > 0
        d = result["defects"][0]
        assert "defect_id" in d
        assert "supplier" in d
        assert "severity" in d

    def test_defects_filter_supplier(self):
        result = query_defect_data("defects", supplier_id="SUP-001")
        assert result["count"] > 0
        # All should be from SUP-001 (check via defect_id presence)
        assert all(isinstance(d["defect_id"], str) for d in result["defects"])

    def test_defects_filter_material(self):
        result = query_defect_data("defects", material_id="MAT-BAT-001")
        assert result["count"] > 0

    def test_defects_filter_severity(self):
        result = query_defect_data("defects", severity="CRITICAL")
        assert result["count"] > 0
        assert all(d["severity"] == "CRITICAL" for d in result["defects"])

    def test_score_valid_supplier(self):
        result = query_defect_data("score", supplier_id="SUP-001")
        assert "defect_score" in result
        assert 0 <= result["defect_score"] <= 10
        assert result["supplier_id"] == "SUP-001"
        assert "supplier_name" in result

    def test_score_no_defects(self):
        result = query_defect_data("score", supplier_id="SUP-999")
        assert result["defect_score"] == 0.0

    def test_score_missing_supplier_id(self):
        result = query_defect_data("score")
        assert "error" in result

    def test_report(self):
        result = query_defect_data("report")
        assert "total" in result
        assert "top_root_causes" in result
        assert "recall_rate_pct" in result
        assert "open_rate_pct" in result

    def test_report_filtered(self):
        result = query_defect_data("report", supplier_id="SUP-001")
        assert "total" in result
        assert result["total"] > 0

    def test_unknown_query_type(self):
        result = query_defect_data("unknown")
        assert "error" in result


class TestInvokeAgentDefects:
    """Test chat agent defect-related queries."""

    def test_defect_summary(self):
        response = invoke_agent("show me defects")
        assert "defect" in response.lower()
        assert "total" in response.lower() or "open" in response.lower()

    def test_defect_supplier_query(self):
        response = invoke_agent("defects for SUP-001")
        assert "defect" in response.lower() or "score" in response.lower()

    def test_defect_material_query(self):
        response = invoke_agent("defects for MAT-BAT-001")
        assert "defect" in response.lower() or "battery" in response.lower()

    def test_recall_query(self):
        response = invoke_agent("any recalls?")
        assert "defect" in response.lower() or "recall" in response.lower()

    def test_quality_issue_query(self):
        response = invoke_agent("quality issues with suppliers")
        assert "defect" in response.lower()

    def test_help_mentions_defects(self):
        response = invoke_agent("help")
        assert "defect" in response.lower()

    def test_how_many_open_defects(self):
        """User asks 'How many defect cases are currently open?'"""
        response = invoke_agent("How many defect cases are currently open?")
        assert "open" in response.lower()
        # Should give a direct number, not just a summary dump
        assert "**7**" in response or "7" in response

    def test_how_many_critical_defects(self):
        response = invoke_agent("How many critical defects are there?")
        assert "critical" in response.lower()
        assert "**4**" in response or "4" in response

    def test_how_many_recalls(self):
        response = invoke_agent("How many recalls have been initiated?")
        assert "recall" in response.lower()
        assert "**6**" in response or "6" in response

    def test_how_many_resolved(self):
        response = invoke_agent("How many defects have been resolved?")
        assert "resolved" in response.lower()

    def test_show_open_defects(self):
        response = invoke_agent("show me open defects")
        assert "open" in response.lower()

    def test_show_critical_defects(self):
        response = invoke_agent("list critical defects")
        assert "critical" in response.lower()

    def test_count_open_cases(self):
        """Natural language: 'count of open defect cases'"""
        response = invoke_agent("what is the count of open defect cases?")
        assert "open" in response.lower()
        assert "7" in response

    def test_total_defects(self):
        response = invoke_agent("total number of defects?")
        # 'total' + 'defect' should trigger, and 'number of' is a count keyword
        # but no specific status filter → should show all counts
        assert "defect" in response.lower()
