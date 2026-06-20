"""
Unit tests for CSV data reader.

Tests data loading, validation, and caching.
Target: 70%+ coverage.
"""

import pytest
from pathlib import Path
from datetime import date

from data.csv_reader import (
    CSVDataReader,
    Supplier,
    Material,
    SupplierMaterial,
    VolumeTier,
    SupplierPerformance
)


class TestCSVDataReader:
    """Test CSV data reader functionality."""

    @pytest.fixture
    def reader(self):
        """Create CSV reader instance."""
        return CSVDataReader(data_dir="../data")

    def test_initialization_success(self, reader):
        """Test successful initialization."""
        assert reader.data_dir == Path("../data")

    def test_initialization_invalid_directory(self):
        """Test initialization with invalid directory."""
        with pytest.raises(FileNotFoundError):
            CSVDataReader(data_dir="nonexistent_directory")

    def test_get_suppliers(self, reader):
        """Test loading suppliers from CSV."""
        suppliers = reader.get_suppliers()

        assert len(suppliers) > 0
        assert all(isinstance(s, Supplier) for s in suppliers)

        # Check first supplier
        sup_001 = next(s for s in suppliers if s.supplier_id == "SUP-001")
        assert sup_001.name == "Shenzhen LiPower Energy Co."
        assert sup_001.rating == 3.2
        assert sup_001.active_status is True
        assert sup_001.financial_stability_score == 5.5
        assert sup_001.geopolitical_risk_score == 6.5

    def test_get_suppliers_caching(self, reader):
        """Test that suppliers are cached."""
        suppliers1 = reader.get_suppliers()
        suppliers2 = reader.get_suppliers()

        # Should return same object (cached)
        assert suppliers1 is suppliers2

    def test_get_materials(self, reader):
        """Test loading materials from CSV."""
        materials = reader.get_materials()

        assert len(materials) > 0
        assert all(isinstance(m, Material) for m in materials)

        # Check battery material
        battery = next(
            m for m in materials
            if m.material_id == "MAT-BAT-001"
        )
        assert "Battery" in battery.name
        assert battery.standard_cost > 0
        assert battery.weight_kg > 0

    def test_get_supplier_materials(self, reader):
        """Test loading supplier-material relationships."""
        supplier_materials = reader.get_supplier_materials()

        assert len(supplier_materials) > 0
        assert all(isinstance(sm, SupplierMaterial) for sm in supplier_materials)

        # Check first relationship
        sm_001 = next(
            sm for sm in supplier_materials
            if sm.supplier_material_id == "SM-001"
        )
        assert sm_001.supplier_id == "SUP-001"
        assert sm_001.material_id == "MAT-BAT-001"
        assert sm_001.base_price > 0
        assert sm_001.minimum_order_quantity > 0
        assert isinstance(sm_001.effective_date, date)

    def test_get_volume_tiers(self, reader):
        """Test loading volume discount tiers."""
        volume_tiers = reader.get_volume_tiers()

        assert len(volume_tiers) > 0
        assert all(isinstance(vt, VolumeTier) for vt in volume_tiers)

        # Check tier structure
        tier_001 = next(
            vt for vt in volume_tiers
            if vt.tier_id == "TIER-001"
        )
        assert tier_001.supplier_material_id == "SM-001"
        assert tier_001.min_quantity > 0
        assert tier_001.discount_percentage >= 0
        assert tier_001.unit_price > 0

    def test_get_volume_tiers_unlimited(self, reader):
        """Test volume tier with unlimited max_quantity."""
        volume_tiers = reader.get_volume_tiers()

        # Find tier with no max_quantity
        unlimited_tier = next(
            vt for vt in volume_tiers
            if vt.max_quantity is None
        )
        assert unlimited_tier is not None
        assert unlimited_tier.min_quantity > 0

    def test_get_supplier_performance(self, reader):
        """Test loading supplier performance metrics."""
        performance = reader.get_supplier_performance()

        assert len(performance) > 0
        assert all(isinstance(p, SupplierPerformance) for p in performance)

        # Check performance record
        perf_001 = next(
            p for p in performance
            if p.performance_id == "PERF-001"
        )
        assert perf_001.supplier_id == "SUP-001"
        assert 0 <= perf_001.on_time_delivery_rate <= 100
        assert 0 <= perf_001.quality_score <= 10
        assert perf_001.response_time_hours > 0

    def test_get_supplier_by_id_found(self, reader):
        """Test getting supplier by ID when exists."""
        supplier = reader.get_supplier_by_id("SUP-001")

        assert supplier is not None
        assert supplier.supplier_id == "SUP-001"
        assert supplier.name == "Shenzhen LiPower Energy Co."

    def test_get_supplier_by_id_not_found(self, reader):
        """Test getting supplier by ID when not exists."""
        supplier = reader.get_supplier_by_id("SUP-999")

        assert supplier is None

    def test_get_material_by_id_found(self, reader):
        """Test getting material by ID when exists."""
        material = reader.get_material_by_id("MAT-BAT-001")

        assert material is not None
        assert material.material_id == "MAT-BAT-001"

    def test_get_material_by_id_not_found(self, reader):
        """Test getting material by ID when not exists."""
        material = reader.get_material_by_id("MAT-999-999")

        assert material is None

    def test_get_suppliers_for_material(self, reader):
        """Test getting all suppliers for a material."""
        suppliers = reader.get_suppliers_for_material("MAT-BAT-001")

        assert len(suppliers) > 0
        assert all(sm.material_id == "MAT-BAT-001" for sm in suppliers)

        # Should have multiple suppliers for batteries
        supplier_ids = {sm.supplier_id for sm in suppliers}
        assert len(supplier_ids) > 1

    def test_get_suppliers_for_material_not_found(self, reader):
        """Test getting suppliers for non-existent material."""
        suppliers = reader.get_suppliers_for_material("MAT-999-999")

        assert len(suppliers) == 0

    def test_get_volume_tiers_for_supplier_material(self, reader):
        """Test getting volume tiers for supplier-material."""
        tiers = reader.get_volume_tiers_for_supplier_material("SM-001")

        assert len(tiers) > 0
        assert all(vt.supplier_material_id == "SM-001" for vt in tiers)

        # Check tiers are sorted by min_quantity
        min_quantities = [vt.min_quantity for vt in tiers]
        assert min_quantities == sorted(min_quantities)

    def test_get_volume_tiers_for_supplier_material_not_found(self, reader):
        """Test getting volume tiers for non-existent supplier-material."""
        tiers = reader.get_volume_tiers_for_supplier_material("SM-999")

        assert len(tiers) == 0

    def test_get_latest_performance(self, reader):
        """Test getting latest performance record."""
        performance = reader.get_latest_performance("SUP-001")

        assert performance is not None
        assert performance.supplier_id == "SUP-001"
        # Should be most recent (2024-01)
        assert performance.measurement_period == "2024-01"

    def test_get_latest_performance_not_found(self, reader):
        """Test getting performance for non-existent supplier."""
        performance = reader.get_latest_performance("SUP-999")

        assert performance is None


class TestDataValidation:
    """Test Pydantic validation rules."""

    def test_supplier_invalid_id_format(self):
        """Test supplier with invalid ID format."""
        with pytest.raises(ValueError):
            Supplier(
                supplier_id="INVALID",
                name="Test Supplier",
                location="Test",
                rating=4.0,
                lead_time_days=30,
                payment_terms="NET 30",
                financial_stability_score=7.0,
                geopolitical_risk_score=2.0,
                active_status=True,
                contact_email="test@test.com",
                contact_phone="+1-555-0100"
            )

    def test_supplier_invalid_rating(self):
        """Test supplier with invalid rating."""
        with pytest.raises(ValueError):
            Supplier(
                supplier_id="SUP-001",
                name="Test Supplier",
                location="Test",
                rating=6.0,  # Invalid: > 5.0
                lead_time_days=30,
                payment_terms="NET 30",
                financial_stability_score=7.0,
                geopolitical_risk_score=2.0,
                active_status=True,
                contact_email="test@test.com",
                contact_phone="+1-555-0100"
            )

    def test_material_invalid_id_format(self):
        """Test material with invalid ID format."""
        with pytest.raises(ValueError):
            Material(
                material_id="INVALID",
                name="Test Material",
                category="TEST",
                unit_of_measure="EACH",
                standard_cost=100.0,
                criticality_level="HIGH",
                weight_kg=1.0
            )

    def test_volume_tier_max_less_than_min(self):
        """Test volume tier with max < min."""
        with pytest.raises(ValueError):
            VolumeTier(
                tier_id="TIER-TEST",
                supplier_material_id="SM-001",
                tier_level=1,
                min_quantity=100,
                max_quantity=50,  # Invalid: < min_quantity
                discount_percentage=5.0,
                unit_price=100.0
            )

    def test_supplier_performance_invalid_rate(self):
        """Test performance with invalid delivery rate."""
        with pytest.raises(ValueError):
            SupplierPerformance(
                performance_id="PERF-TEST",
                supplier_id="SUP-001",
                measurement_period="2024-01",
                on_time_delivery_rate=150.0,  # Invalid: > 100
                quality_score=8.0,
                defect_rate=2.0,
                cost_variance=-1.0,
                response_time_hours=24
            )
