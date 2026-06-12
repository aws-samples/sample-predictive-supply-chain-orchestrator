"""
Tests for NeptuneDataReader class.

Tests the Neptune data reader with mocked HTTP queries.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date
from data.neptune_data_reader import NeptuneDataReader
from data.csv_reader import Supplier, Material, SupplierMaterial


class TestNeptuneDataReader:
    """Test suite for NeptuneDataReader."""

    @pytest.fixture
    def mock_neptune_response(self):
        """Mock Neptune GraphSON response for suppliers."""
        return {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "name", "Acme Electronics",
                        "location", "China",
                        "rating", {"@type": "g:Double", "@value": 4.5},
                        "lead_time_days", {"@type": "g:Int32", "@value": 30},
                        "payment_terms", "Net 30",
                        "financial_stability_score", {"@type": "g:Double", "@value": 8.5},
                        "geopolitical_risk_score", {"@type": "g:Double", "@value": 3.2},
                        "active_status", True,
                        "contact_email", "contact@acme.com",
                        "contact_phone", "+1-555-1234"
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-002",
                        "name", "Battery Corp",
                        "location", "USA",
                        "rating", {"@type": "g:Double", "@value": 4.2},
                        "lead_time_days", {"@type": "g:Int32", "@value": 45},
                        "payment_terms", "Net 60",
                        "financial_stability_score", {"@type": "g:Double", "@value": 9.0},
                        "geopolitical_risk_score", {"@type": "g:Double", "@value": 1.5},
                        "active_status", True,
                        "contact_email", "info@batterycorp.com",
                        "contact_phone", "+1-555-5678"
                    ]
                }
            ]
        }

    @pytest.fixture
    def reader(self):
        """Create a NeptuneDataReader instance with mocked endpoint."""
        with patch.dict("os.environ", {"NEPTUNE_ENDPOINT": "test.neptune.amazonaws.com"}):
            return NeptuneDataReader()

    def test_init_with_endpoint(self):
        """Test initialization with explicit endpoint."""
        reader = NeptuneDataReader(endpoint="test.neptune.com", port=8182)
        assert reader.endpoint == "test.neptune.com"
        assert reader.port == 8182

    def test_init_from_env(self):
        """Test initialization from environment variables."""
        with patch.dict("os.environ", {
            "NEPTUNE_ENDPOINT": "env.neptune.com",
            "NEPTUNE_PORT": "9999"
        }):
            reader = NeptuneDataReader()
            assert reader.endpoint == "env.neptune.com"
            assert reader.port == 9999

    def test_init_missing_endpoint(self):
        """Test initialization fails without endpoint."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="NEPTUNE_ENDPOINT must be set"):
                NeptuneDataReader()

    def test_parse_results_graphson_list(self, reader):
        """Test parsing GraphSON g:List response."""
        raw = {
            "@type": "g:List",
            "@value": [
                {"@type": "g:Map", "@value": ["key1", "value1", "key2", {"@type": "g:Int32", "@value": 42}]},
                {"@type": "g:Map", "@value": ["key3", {"@type": "g:Double", "@value": 3.14}]}
            ]
        }
        result = reader._parse_results(raw)
        assert len(result) == 2
        assert result[0] == {"key1": "value1", "key2": 42}
        assert result[1] == {"key3": 3.14}

    def test_parse_results_plain_list(self, reader):
        """Test parsing plain list response."""
        raw = [
            {"name": "test1", "value": 1},
            {"name": "test2", "value": 2}
        ]
        result = reader._parse_results(raw)
        assert result == raw

    def test_parse_results_nested_types(self, reader):
        """Test parsing nested GraphSON types."""
        raw = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "numbers", {"@type": "g:List", "@value": [
                            {"@type": "g:Int32", "@value": 1},
                            {"@type": "g:Int32", "@value": 2}
                        ]},
                        "nested", {"@type": "g:Map", "@value": [
                            "key", {"@type": "g:Double", "@value": 1.5}
                        ]}
                    ]
                }
            ]
        }
        result = reader._parse_results(raw)
        assert len(result) == 1
        assert result[0]["numbers"] == [1, 2]
        assert result[0]["nested"] == {"key": 1.5}

    def test_get_suppliers_success(self, reader, mock_neptune_response):
        """Test successful retrieval of suppliers from Neptune."""
        with patch.object(reader, "_http_query", return_value=mock_neptune_response):
            suppliers = reader.get_suppliers()

            assert len(suppliers) == 2
            assert all(isinstance(s, Supplier) for s in suppliers)

            # Check first supplier
            assert suppliers[0].supplier_id == "SUP-001"
            assert suppliers[0].name == "Acme Electronics"
            assert suppliers[0].location == "China"
            assert suppliers[0].rating == 4.5
            assert suppliers[0].lead_time_days == 30
            assert suppliers[0].financial_stability_score == 8.5
            assert suppliers[0].geopolitical_risk_score == 3.2
            assert suppliers[0].active_status is True

            # Check second supplier
            assert suppliers[1].supplier_id == "SUP-002"
            assert suppliers[1].name == "Battery Corp"
            assert suppliers[1].location == "USA"
            assert suppliers[1].rating == 4.2

    def test_get_suppliers_caching(self, reader, mock_neptune_response):
        """Test that get_suppliers uses caching."""
        with patch.object(reader, "_http_query", return_value=mock_neptune_response) as mock_query:
            # First call
            suppliers1 = reader.get_suppliers()
            assert mock_query.call_count == 1

            # Second call should use cache
            suppliers2 = reader.get_suppliers()
            assert mock_query.call_count == 1  # Still 1, not 2

            # Verify same objects returned
            assert suppliers1 is suppliers2

    def test_get_suppliers_with_invalid_data(self, reader):
        """Test get_suppliers handles invalid data gracefully."""
        # Response with one valid and one invalid supplier
        invalid_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "name", "Valid Supplier",
                        "location", "USA",
                        "rating", {"@type": "g:Double", "@value": 4.5},
                        "lead_time_days", {"@type": "g:Int32", "@value": 30},
                        "payment_terms", "Net 30",
                        "financial_stability_score", {"@type": "g:Double", "@value": 8.5},
                        "geopolitical_risk_score", {"@type": "g:Double", "@value": 3.2},
                        "active_status", True,
                        "contact_email", "contact@valid.com",
                        "contact_phone", "+1-555-1234"
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "INVALID-ID",  # Invalid ID format
                        "name", "Invalid Supplier",
                        "rating", {"@type": "g:Double", "@value": 15.0}  # Invalid rating (>5.0)
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=invalid_response):
            suppliers = reader.get_suppliers()

            # Should only get valid supplier, invalid one should be skipped
            assert len(suppliers) == 1
            assert suppliers[0].supplier_id == "SUP-001"

    def test_get_suppliers_with_missing_fields(self, reader):
        """Test get_suppliers handles missing optional fields."""
        response_with_defaults = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-003",
                        "name", "Minimal Supplier",
                        "location", "UK",
                        "rating", {"@type": "g:Double", "@value": 3.0},
                        "lead_time_days", {"@type": "g:Int32", "@value": 20},
                        "payment_terms", "Net 45",
                        "financial_stability_score", {"@type": "g:Double", "@value": 5.0},
                        "geopolitical_risk_score", {"@type": "g:Double", "@value": 2.0},
                        "active_status", True,
                        "contact_email", "test@minimal.com",
                        "contact_phone", "+44-555-1234"
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=response_with_defaults):
            suppliers = reader.get_suppliers()

            assert len(suppliers) == 1
            assert suppliers[0].supplier_id == "SUP-003"

    def test_get_suppliers_query_failure(self, reader):
        """Test get_suppliers handles query failures."""
        with patch.object(reader, "_http_query", side_effect=Exception("Connection failed")):
            with pytest.raises(ValueError, match="Failed to load suppliers from Neptune"):
                reader.get_suppliers()

    def test_get_suppliers_empty_response(self, reader):
        """Test get_suppliers with empty response."""
        empty_response = {"@type": "g:List", "@value": []}

        with patch.object(reader, "_http_query", return_value=empty_response):
            suppliers = reader.get_suppliers()
            assert len(suppliers) == 0

    @pytest.fixture
    def mock_materials_response(self):
        """Mock Neptune GraphSON response for materials."""
        return {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "MAT-BAT-001",
                        "name", "Lithium Battery",
                        "category", "Battery",
                        "unit_of_measure", "unit",
                        "standard_cost", {"@type": "g:Double", "@value": 50.0},
                        "criticality_level", "High",
                        "weight_kg", {"@type": "g:Double", "@value": 0.5}
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "MAT-ELE-001",
                        "name", "Resistor 10K",
                        "category", "Electronics",
                        "unit_of_measure", "unit",
                        "standard_cost", {"@type": "g:Double", "@value": 0.05},
                        "criticality_level", "Low",
                        "weight_kg", {"@type": "g:Double", "@value": 0.001}
                    ]
                }
            ]
        }

    @pytest.fixture
    def mock_supplier_materials_response(self):
        """Mock Neptune GraphSON response for supplier-material edges."""
        return {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "edge", {
                            "@type": "g:Map",
                            "@value": [
                                "id", "SM-001",
                                "base_price", {"@type": "g:Double", "@value": 45.50},
                                "currency", "USD",
                                "effective_date", "2024-01-01",
                                "minimum_order_quantity", {"@type": "g:Int32", "@value": 100},
                                "lead_time_days", {"@type": "g:Int32", "@value": 30},
                                "quality_certification", "ISO9001",
                                "sustainability_score", {"@type": "g:Double", "@value": 8.5},
                                "carbon_footprint_kg", {"@type": "g:Double", "@value": 0.25}
                            ]
                        },
                        "src", "SUP-001",
                        "dst", "MAT-BAT-001"
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "edge", {
                            "@type": "g:Map",
                            "@value": [
                                "id", "SM-002",
                                "base_price", {"@type": "g:Double", "@value": 47.00},
                                "currency", "USD",
                                "effective_date", "2024-02-01",
                                "minimum_order_quantity", {"@type": "g:Int32", "@value": 50},
                                "lead_time_days", {"@type": "g:Int32", "@value": 45},
                                "quality_certification", "ISO14001",
                                "sustainability_score", {"@type": "g:Double", "@value": 9.0},
                                "carbon_footprint_kg", {"@type": "g:Double", "@value": 0.20}
                            ]
                        },
                        "src", "SUP-002",
                        "dst", "MAT-BAT-001"
                    ]
                }
            ]
        }

    def test_get_materials_success(self, reader, mock_materials_response):
        """Test successful retrieval of materials from Neptune."""
        with patch.object(reader, "_http_query", return_value=mock_materials_response):
            materials = reader.get_materials()

            assert len(materials) == 2
            assert all(isinstance(m, Material) for m in materials)

            # Check first material
            assert materials[0].material_id == "MAT-BAT-001"
            assert materials[0].name == "Lithium Battery"
            assert materials[0].category == "Battery"
            assert materials[0].unit_of_measure == "unit"
            assert materials[0].standard_cost == 50.0
            assert materials[0].criticality_level == "High"
            assert materials[0].weight_kg == 0.5

            # Check second material
            assert materials[1].material_id == "MAT-ELE-001"
            assert materials[1].name == "Resistor 10K"
            assert materials[1].standard_cost == 0.05

    def test_get_materials_caching(self, reader, mock_materials_response):
        """Test that get_materials uses caching."""
        with patch.object(reader, "_http_query", return_value=mock_materials_response) as mock_query:
            # First call
            materials1 = reader.get_materials()
            assert mock_query.call_count == 1

            # Second call should use cache
            materials2 = reader.get_materials()
            assert mock_query.call_count == 1  # Still 1, not 2

            # Verify same objects returned
            assert materials1 is materials2

    def test_get_materials_with_invalid_data(self, reader):
        """Test get_materials handles invalid data gracefully."""
        invalid_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "MAT-BAT-001",
                        "name", "Valid Material",
                        "category", "Battery",
                        "unit_of_measure", "unit",
                        "standard_cost", {"@type": "g:Double", "@value": 50.0},
                        "criticality_level", "High",
                        "weight_kg", {"@type": "g:Double", "@value": 0.5}
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "INVALID-ID",  # Invalid ID format
                        "name", "Invalid Material",
                        "standard_cost", {"@type": "g:Double", "@value": -10.0}  # Invalid cost
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=invalid_response):
            materials = reader.get_materials()

            # Should only get valid material, invalid one should be skipped
            assert len(materials) == 1
            assert materials[0].material_id == "MAT-BAT-001"

    def test_get_materials_query_failure(self, reader):
        """Test get_materials handles query failures."""
        with patch.object(reader, "_http_query", side_effect=Exception("Connection failed")):
            with pytest.raises(ValueError, match="Failed to load materials from Neptune"):
                reader.get_materials()

    def test_get_materials_empty_response(self, reader):
        """Test get_materials with empty response."""
        empty_response = {"@type": "g:List", "@value": []}

        with patch.object(reader, "_http_query", return_value=empty_response):
            materials = reader.get_materials()
            assert len(materials) == 0

    def test_get_supplier_materials_success(self, reader, mock_supplier_materials_response):
        """Test successful retrieval of supplier-material edges from Neptune."""
        with patch.object(reader, "_http_query", return_value=mock_supplier_materials_response):
            supplier_materials = reader.get_supplier_materials()

            assert len(supplier_materials) == 2
            assert all(isinstance(sm, SupplierMaterial) for sm in supplier_materials)

            # Check first supplier-material
            assert supplier_materials[0].supplier_material_id == "SM-001"
            assert supplier_materials[0].supplier_id == "SUP-001"
            assert supplier_materials[0].material_id == "MAT-BAT-001"
            assert supplier_materials[0].base_price == 45.50
            assert supplier_materials[0].currency == "USD"
            assert supplier_materials[0].effective_date == date(2024, 1, 1)
            assert supplier_materials[0].minimum_order_quantity == 100
            assert supplier_materials[0].lead_time_days == 30
            assert supplier_materials[0].quality_certification == "ISO9001"
            assert supplier_materials[0].sustainability_score == 8.5
            assert supplier_materials[0].carbon_footprint_kg == 0.25

            # Check second supplier-material
            assert supplier_materials[1].supplier_material_id == "SM-002"
            assert supplier_materials[1].supplier_id == "SUP-002"
            assert supplier_materials[1].material_id == "MAT-BAT-001"
            assert supplier_materials[1].base_price == 47.00
            assert supplier_materials[1].effective_date == date(2024, 2, 1)

    def test_get_supplier_materials_caching(self, reader, mock_supplier_materials_response):
        """Test that get_supplier_materials uses caching."""
        with patch.object(reader, "_http_query", return_value=mock_supplier_materials_response) as mock_query:
            # First call
            sm1 = reader.get_supplier_materials()
            assert mock_query.call_count == 1

            # Second call should use cache
            sm2 = reader.get_supplier_materials()
            assert mock_query.call_count == 1  # Still 1, not 2

            # Verify same objects returned
            assert sm1 is sm2

    def test_get_supplier_materials_with_invalid_data(self, reader):
        """Test get_supplier_materials handles invalid data gracefully."""
        invalid_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "edge", {
                            "@type": "g:Map",
                            "@value": [
                                "id", "SM-001",
                                "base_price", {"@type": "g:Double", "@value": 45.50},
                                "currency", "USD",
                                "effective_date", "2024-01-01",
                                "minimum_order_quantity", {"@type": "g:Int32", "@value": 100},
                                "lead_time_days", {"@type": "g:Int32", "@value": 30},
                                "quality_certification", "ISO9001",
                                "sustainability_score", {"@type": "g:Double", "@value": 8.5},
                                "carbon_footprint_kg", {"@type": "g:Double", "@value": 0.25}
                            ]
                        },
                        "src", "SUP-001",
                        "dst", "MAT-BAT-001"
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "edge", {
                            "@type": "g:Map",
                            "@value": [
                                "id", "SM-002",
                                "base_price", {"@type": "g:Double", "@value": -10.0},  # Invalid price
                                "currency", "USD",
                                "effective_date", "2024-02-01",
                                "minimum_order_quantity", {"@type": "g:Int32", "@value": 0},  # Invalid MOQ
                                "lead_time_days", {"@type": "g:Int32", "@value": 0}  # Invalid lead time
                            ]
                        },
                        "src", "SUP-002",
                        "dst", "MAT-BAT-001"
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=invalid_response):
            supplier_materials = reader.get_supplier_materials()

            # Should only get valid supplier-material, invalid one should be skipped
            assert len(supplier_materials) == 1
            assert supplier_materials[0].supplier_material_id == "SM-001"

    def test_get_supplier_materials_query_failure(self, reader):
        """Test get_supplier_materials handles query failures."""
        with patch.object(reader, "_http_query", side_effect=Exception("Connection failed")):
            with pytest.raises(ValueError, match="Failed to load supplier materials from Neptune"):
                reader.get_supplier_materials()

    def test_get_supplier_materials_empty_response(self, reader):
        """Test get_supplier_materials with empty response."""
        empty_response = {"@type": "g:List", "@value": []}

        with patch.object(reader, "_http_query", return_value=empty_response):
            supplier_materials = reader.get_supplier_materials()
            assert len(supplier_materials) == 0

    def test_get_supplier_materials_date_parsing(self, reader):
        """Test get_supplier_materials handles various date formats."""
        response_with_dates = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "edge", {
                            "@type": "g:Map",
                            "@value": [
                                "id", "SM-003",
                                "base_price", {"@type": "g:Double", "@value": 50.0},
                                "currency", "USD",
                                "effective_date", "2024-03-15",  # String date
                                "minimum_order_quantity", {"@type": "g:Int32", "@value": 10},
                                "lead_time_days", {"@type": "g:Int32", "@value": 20},
                                "quality_certification", "ISO9001",
                                "sustainability_score", {"@type": "g:Double", "@value": 7.0},
                                "carbon_footprint_kg", {"@type": "g:Double", "@value": 0.3}
                            ]
                        },
                        "src", "SUP-003",
                        "dst", "MAT-ELE-001"
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=response_with_dates):
            supplier_materials = reader.get_supplier_materials()

            assert len(supplier_materials) == 1
            assert supplier_materials[0].effective_date == date(2024, 3, 15)

    # Tests for simple lookup methods

    def test_get_supplier_by_id_found(self, reader, mock_neptune_response):
        """Test getting supplier by ID when it exists."""
        with patch.object(reader, "_http_query", return_value=mock_neptune_response):
            supplier = reader.get_supplier_by_id("SUP-001")
            assert supplier is not None
            assert supplier.supplier_id == "SUP-001"
            assert supplier.name == "Acme Electronics"

    def test_get_supplier_by_id_not_found(self, reader, mock_neptune_response):
        """Test getting supplier by ID when it doesn't exist."""
        with patch.object(reader, "_http_query", return_value=mock_neptune_response):
            supplier = reader.get_supplier_by_id("SUP-999")
            assert supplier is None

    def test_get_material_by_id_found(self, reader, mock_materials_response):
        """Test getting material by ID when it exists."""
        with patch.object(reader, "_http_query", return_value=mock_materials_response):
            material = reader.get_material_by_id("MAT-BAT-001")
            assert material is not None
            assert material.material_id == "MAT-BAT-001"
            assert material.name == "Lithium Battery"

    def test_get_material_by_id_not_found(self, reader, mock_materials_response):
        """Test getting material by ID when it doesn't exist."""
        with patch.object(reader, "_http_query", return_value=mock_materials_response):
            material = reader.get_material_by_id("MAT-XXX-999")
            assert material is None

    def test_get_suppliers_for_material(self, reader, mock_supplier_materials_response):
        """Test getting all suppliers for a material."""
        with patch.object(reader, "_http_query", return_value=mock_supplier_materials_response):
            suppliers = reader.get_suppliers_for_material("MAT-BAT-001")
            assert len(suppliers) == 2
            assert all(sm.material_id == "MAT-BAT-001" for sm in suppliers)
            assert suppliers[0].supplier_id == "SUP-001"
            assert suppliers[1].supplier_id == "SUP-002"

    def test_get_suppliers_for_material_none_found(self, reader, mock_supplier_materials_response):
        """Test getting suppliers for material with none available."""
        with patch.object(reader, "_http_query", return_value=mock_supplier_materials_response):
            suppliers = reader.get_suppliers_for_material("MAT-XXX-999")
            assert len(suppliers) == 0

    # Tests for performance history methods

    def test_get_performance_history(self, reader):
        """Test getting performance history for a supplier."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "measurement_period", "2024-01",
                        "on_time_delivery_rate", {"@type": "g:Double", "@value": 95.5},
                        "quality_score", {"@type": "g:Double", "@value": 8.5},
                        "defect_rate", {"@type": "g:Double", "@value": 0.5},
                        "cost_variance", {"@type": "g:Double", "@value": 2.3},
                        "response_time_hours", {"@type": "g:Int32", "@value": 24}
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            history = reader.get_performance_history("SUP-001")
            assert len(history) == 1
            assert history[0].supplier_id == "SUP-001"
            assert history[0].on_time_delivery_rate == 95.5
            assert history[0].quality_score == 8.5
            assert history[0].defect_rate == 0.5
            assert history[0].cost_variance == 2.3
            assert history[0].response_time_hours == 24

    def test_get_performance_history_empty(self, reader):
        """Test getting performance history when none exists."""
        empty_response = {"@type": "g:List", "@value": []}

        with patch.object(reader, "_http_query", return_value=empty_response):
            history = reader.get_performance_history("SUP-999")
            assert len(history) == 0

    def test_get_performance_history_caching(self, reader):
        """Test that performance history uses caching."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "measurement_period", "2024-01",
                        "on_time_delivery_rate", {"@type": "g:Double", "@value": 95.5},
                        "quality_score", {"@type": "g:Double", "@value": 8.5},
                        "defect_rate", {"@type": "g:Double", "@value": 0.5},
                        "cost_variance", {"@type": "g:Double", "@value": 2.3},
                        "response_time_hours", {"@type": "g:Int32", "@value": 24}
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response) as mock_query:
            # First call
            history1 = reader.get_performance_history("SUP-001")
            assert mock_query.call_count == 1

            # Second call should use cache
            history2 = reader.get_performance_history("SUP-001")
            assert mock_query.call_count == 1  # Still 1, not 2

            # Verify same data returned
            assert len(history1) == len(history2)

    def test_get_latest_performance(self, reader):
        """Test getting latest performance record."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "measurement_period", "2024-03",
                        "on_time_delivery_rate", {"@type": "g:Double", "@value": 96.0},
                        "quality_score", {"@type": "g:Double", "@value": 9.0},
                        "defect_rate", {"@type": "g:Double", "@value": 0.3},
                        "cost_variance", {"@type": "g:Double", "@value": 1.5},
                        "response_time_hours", {"@type": "g:Int32", "@value": 20}
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            latest = reader.get_latest_performance("SUP-001")
            assert latest is not None
            assert latest.supplier_id == "SUP-001"
            assert latest.measurement_period == "2024-03"

    def test_get_latest_performance_none(self, reader):
        """Test getting latest performance when none exists."""
        empty_response = {"@type": "g:List", "@value": []}

        with patch.object(reader, "_http_query", return_value=empty_response):
            latest = reader.get_latest_performance("SUP-999")
            assert latest is None

    # Tests for contract methods

    def test_get_contract_for_supplier(self, reader):
        """Test getting contract for a supplier."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "contract_type", "Long-term",
                        "payment_terms", "Net 45",
                        "annual_value", {"@type": "g:Double", "@value": 500000.0},
                        "contract_start_date", "2024-01-01",
                        "contract_end_date", "2025-12-31",
                        "volume_commitment", "High",
                        "contract_status", "Active"
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            contract = reader.get_contract_for_supplier("SUP-001")
            assert contract is not None
            assert contract.supplier_id == "SUP-001"
            assert contract.contract_type == "Long-term"
            assert contract.payment_terms == "Net 45"
            assert contract.annual_value == 500000.0
            assert contract.status == "Active"

    def test_get_contract_for_supplier_no_contract(self, reader):
        """Test getting contract when supplier has no contract properties."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-002",
                        "name", "Some Supplier",
                        "location", "USA"
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            contract = reader.get_contract_for_supplier("SUP-002")
            assert contract is None

    def test_get_contract_for_supplier_caching(self, reader):
        """Test that contract queries use caching."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SUP-001",
                        "contract_type", "Long-term",
                        "payment_terms", "Net 45",
                        "annual_value", {"@type": "g:Double", "@value": 500000.0},
                        "contract_start_date", "2024-01-01",
                        "contract_end_date", "2025-12-31",
                        "volume_commitment", "High",
                        "contract_status", "Active"
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response) as mock_query:
            # First call
            contract1 = reader.get_contract_for_supplier("SUP-001")
            assert mock_query.call_count == 1

            # Second call should use cache
            contract2 = reader.get_contract_for_supplier("SUP-001")
            assert mock_query.call_count == 1  # Still 1, not 2

            assert contract1 is contract2

    # Tests for volume tier methods

    def test_get_volume_tiers_for_supplier_material(self, reader):
        """Test getting volume tiers for supplier-material edge."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SM-001",
                        "volume_tiers", '[{"tier_level": 1, "min_quantity": 100, "max_quantity": 499, "discount_percentage": 5.0, "unit_price": 45.0}, {"tier_level": 2, "min_quantity": 500, "max_quantity": null, "discount_percentage": 10.0, "unit_price": 42.0}]'
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            tiers = reader.get_volume_tiers_for_supplier_material("SM-001")
            assert len(tiers) == 2
            assert tiers[0].tier_level == 1
            assert tiers[0].min_quantity == 100
            assert tiers[0].max_quantity == 499
            assert tiers[0].discount_percentage == 5.0
            assert tiers[0].unit_price == 45.0
            assert tiers[1].tier_level == 2
            assert tiers[1].min_quantity == 500
            assert tiers[1].max_quantity is None
            assert tiers[1].discount_percentage == 10.0

    def test_get_volume_tiers_for_supplier_material_empty(self, reader):
        """Test getting volume tiers when none exist."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SM-002",
                        "base_price", {"@type": "g:Double", "@value": 50.0}
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            tiers = reader.get_volume_tiers_for_supplier_material("SM-002")
            assert len(tiers) == 0

    def test_get_volume_tiers_caching(self, reader):
        """Test that volume tiers use caching."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "SM-001",
                        "volume_tiers", '[{"tier_level": 1, "min_quantity": 100, "max_quantity": 499, "discount_percentage": 5.0, "unit_price": 45.0}]'
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response) as mock_query:
            # First call
            tiers1 = reader.get_volume_tiers_for_supplier_material("SM-001")
            assert mock_query.call_count == 1

            # Second call should use cache
            tiers2 = reader.get_volume_tiers_for_supplier_material("SM-001")
            assert mock_query.call_count == 1  # Still 1, not 2

            assert len(tiers1) == len(tiers2)

    # Tests for defect score calculation

    def test_get_supplier_defect_score_no_defects(self, reader):
        """Test defect score calculation with no defects."""
        empty_response = {"@type": "g:List", "@value": []}

        with patch.object(reader, "_http_query", return_value=empty_response):
            score = reader.get_supplier_defect_score("SUP-001")
            assert score == 0.0

    def test_get_supplier_defect_score_with_defects(self, reader):
        """Test defect score calculation with various defects."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "DEF-001",
                        "severity", "CRITICAL",
                        "status", "OPEN",
                        "recall_initiated", True
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "DEF-002",
                        "severity", "MAJOR",
                        "status", "RESOLVED",
                        "recall_initiated", False
                    ]
                },
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "DEF-003",
                        "severity", "MINOR",
                        "status", "CLOSED",
                        "recall_initiated", False
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            score = reader.get_supplier_defect_score("SUP-001")
            # CRITICAL (3.0) * OPEN (1.5) * RECALL (1.5) = 6.75
            # MAJOR (2.0) * RESOLVED (0.8) * NO_RECALL (1.0) = 1.6
            # MINOR (1.0) * CLOSED (0.5) * NO_RECALL (1.0) = 0.5
            # Total = 8.85
            assert score > 8.0
            assert score < 10.0

    def test_get_supplier_defect_score_capped_at_10(self, reader):
        """Test that defect score is capped at 10.0."""
        # Create many critical defects
        defects = []
        for i in range(10):
            defects.append({
                "@type": "g:Map",
                "@value": [
                    "id", f"DEF-{i:03d}",
                    "severity", "CRITICAL",
                    "status", "OPEN",
                    "recall_initiated", True
                ]
            })

        mock_response = {
            "@type": "g:List",
            "@value": defects
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            score = reader.get_supplier_defect_score("SUP-001")
            assert score == 10.0

    def test_get_supplier_defect_score_caching(self, reader):
        """Test that defect score uses caching."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "DEF-001",
                        "severity", "MAJOR",
                        "status", "OPEN",
                        "recall_initiated", False
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response) as mock_query:
            # First call
            score1 = reader.get_supplier_defect_score("SUP-001")
            assert mock_query.call_count == 1

            # Second call should use cache
            score2 = reader.get_supplier_defect_score("SUP-001")
            assert mock_query.call_count == 1  # Still 1, not 2

            assert score1 == score2

    def test_get_supplier_defect_score_string_boolean(self, reader):
        """Test defect score handles string boolean values."""
        mock_response = {
            "@type": "g:List",
            "@value": [
                {
                    "@type": "g:Map",
                    "@value": [
                        "id", "DEF-001",
                        "severity", "CRITICAL",
                        "status", "OPEN",
                        "recall_initiated", "TRUE"  # String instead of boolean
                    ]
                }
            ]
        }

        with patch.object(reader, "_http_query", return_value=mock_response):
            score = reader.get_supplier_defect_score("SUP-001")
            # Should handle string boolean correctly
            # CRITICAL (3.0) * OPEN (1.5) * RECALL (1.5) = 6.75
            assert score > 6.0
            assert score < 7.0
