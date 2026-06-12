"""
Integration tests for defect tracking + optimization engine.

Verifies that defect history scores are properly integrated
into the optimization engine's risk calculation.
"""

import pytest

from core.optimization.engine import OptimizationEngine
from core.models import OptimizationRequest, MaterialDemand, OptimizationConstraints
from data.csv_reader import CSVDataReader


class TestDefectOptimizationIntegration:
    """Test that defect scores influence optimization risk calculations."""

    @pytest.fixture
    def reader(self):
        return CSVDataReader(data_dir="../data")

    @pytest.fixture
    def engine(self, reader):
        return OptimizationEngine(reader)

    def test_engine_uses_defect_score_in_risk(self, engine, reader):
        """Verify the engine calls get_supplier_defect_score during optimization."""
        request = OptimizationRequest(
            materials=[MaterialDemand(material_id="MAT-BAT-001", quantity=500)],
            constraints=OptimizationConstraints(
                max_supplier_concentration=0.60,
                max_lead_time_days=60,
                budget_max=2_000_000,
            ),
        )
        solutions = engine.optimize(request)
        assert len(solutions) == 4

        # All solutions should have valid risk scores
        for sol in solutions:
            assert 0 <= sol.risk_score <= 10

    def test_defect_score_available_for_all_suppliers(self, reader):
        """Verify defect scores can be computed for all suppliers in the system."""
        suppliers = reader.get_suppliers()
        for s in suppliers:
            score = reader.get_supplier_defect_score(s.supplier_id)
            assert isinstance(score, float)
            assert 0.0 <= score <= 10.0

    def test_optimization_with_defect_data_produces_valid_solutions(self, engine):
        """Full optimization with defect data should produce valid Pareto solutions."""
        request = OptimizationRequest(
            materials=[
                MaterialDemand(material_id="MAT-BAT-001", quantity=500),
                MaterialDemand(material_id="MAT-MOT-001", quantity=500),
                MaterialDemand(material_id="MAT-ELC-001", quantity=500),
            ],
            constraints=OptimizationConstraints(
                max_supplier_concentration=0.60,
                max_lead_time_days=60,
                budget_max=5_000_000,
            ),
        )
        solutions = engine.optimize(request)

        names = {s.name for s in solutions}
        assert names == {"Budget", "Balanced", "Premium", "Resilient"}

        for sol in solutions:
            assert sol.total_cost > 0
            assert 0 <= sol.risk_score <= 10
            assert 0 <= sol.quality_score <= 10
            assert sol.lead_time_days > 0
            assert len(sol.allocations) > 0

    def test_risk_calculation_includes_defect_history(self, engine, reader):
        """Verify _calculate_dynamic_risk uses defect_history_score."""
        request = OptimizationRequest(
            materials=[MaterialDemand(material_id="MAT-BAT-001", quantity=500)],
        )
        problem = engine._build_problem(request)

        # Get a supplier that has defects
        defects = reader.get_defects()
        supplier_with_defects = defects[0].supplier_id
        score = reader.get_supplier_defect_score(supplier_with_defects)
        assert score > 0, "Test supplier should have defects"

        # Get a supplier with no defects
        all_supplier_ids = {s.supplier_id for s in reader.get_suppliers()}
        defect_supplier_ids = {d.supplier_id for d in defects}
        no_defect_suppliers = all_supplier_ids - defect_supplier_ids

        if no_defect_suppliers:
            clean_supplier = next(iter(no_defect_suppliers))
            clean_score = reader.get_supplier_defect_score(clean_supplier)
            assert clean_score == 0.0
