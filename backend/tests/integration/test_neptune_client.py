"""
Integration tests for Neptune client.

Uses mocking for Gremlin client.
Follows CDE standards: 70%+ coverage target.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from gremlin_python.driver.protocol import GremlinServerError

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from data.neptune_client import NeptuneClient


class TestNeptuneClient:
    """Test suite for NeptuneClient class."""
    
    def test_init_with_endpoint(self):
        """Test client initialization with endpoint."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com",
            port=8182
        )
        
        assert client.endpoint == "test-cluster.us-east-1.neptune.amazonaws.com"
        assert client.port == 8182
        assert "wss://" in client.connection_string
    
    def test_init_without_endpoint_raises_error(self):
        """Test that missing endpoint raises ValueError."""
        with patch("data.neptune_client.settings") as mock_settings:
            mock_settings.neptune_endpoint = ""
            mock_settings.neptune_port = 8182
            
            with pytest.raises(ValueError, match="NEPTUNE_ENDPOINT must be set"):
                NeptuneClient()
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_get_client_creates_connection(self, mock_gremlin_client):
        """Test that _get_client creates Gremlin client."""
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        result = client._get_client()
        
        assert result == mock_client_instance
        mock_gremlin_client.assert_called_once()
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_get_client_reuses_connection(self, mock_gremlin_client):
        """Test that _get_client reuses existing connection."""
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        # Call twice
        result1 = client._get_client()
        result2 = client._get_client()
        
        assert result1 == result2
        mock_gremlin_client.assert_called_once()  # Only called once
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_find_alternative_suppliers_success(self, mock_gremlin_client):
        """Test finding alternative suppliers."""
        # Setup mock
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        mock_result = Mock()
        mock_result.all.return_value.result.return_value = [
            {
                "supplier_id": "SUP-002",
                "name": "Alternative Supplier",
                "rating": 4.5,
                "distance": 1
            }
        ]
        mock_client_instance.submit.return_value = mock_result
        
        # Test
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        results = client.find_alternative_suppliers("MAT-001", max_hops=2)
        
        # Verify
        assert len(results) == 1
        assert results[0]["supplier_id"] == "SUP-002"
        mock_client_instance.submit.assert_called_once()
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_find_alternative_suppliers_empty_material_id(self, mock_gremlin_client):
        """Test validation for empty material ID."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        with pytest.raises(ValueError, match="material_id cannot be empty"):
            client.find_alternative_suppliers("", max_hops=2)
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_find_alternative_suppliers_invalid_max_hops(self, mock_gremlin_client):
        """Test validation for invalid max_hops."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        with pytest.raises(ValueError, match="max_hops must be between 1 and 3"):
            client.find_alternative_suppliers("MAT-001", max_hops=5)
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_find_alternative_suppliers_gremlin_error(self, mock_gremlin_client):
        """Test handling of Gremlin server errors."""
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        mock_client_instance.submit.side_effect = GremlinServerError(
            {"code": 500, "message": "Query error", "attributes": {}}
        )
        
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        with pytest.raises(GremlinServerError):
            client.find_alternative_suppliers("MAT-001")
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_get_supplier_network_success(self, mock_gremlin_client):
        """Test getting supplier network."""
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        mock_result = Mock()
        mock_result.all.return_value.result.return_value = [
            {
                "supplier": {"id": "SUP-001", "name": "Test Supplier"},
                "material": {"id": "MAT-001", "name": "Test Material"}
            }
        ]
        mock_client_instance.submit.return_value = mock_result
        
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        result = client.get_supplier_network("SUP-001")
        
        assert "supplier_id" in result
        assert "relationships" in result
        assert len(result["relationships"]) == 1
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_get_supplier_network_empty_supplier_id(self, mock_gremlin_client):
        """Test validation for empty supplier ID."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        with pytest.raises(ValueError, match="supplier_id cannot be empty"):
            client.get_supplier_network("")
    
    def test_calculate_supplier_concentration(self):
        """Test supplier concentration calculation."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        allocations = [
            {"supplier_id": "SUP-001", "quantity": 300},
            {"supplier_id": "SUP-002", "quantity": 200},
            {"supplier_id": "SUP-001", "quantity": 100}
        ]
        
        concentration = client.calculate_supplier_concentration(allocations)
        
        assert "SUP-001" in concentration
        assert "SUP-002" in concentration
        assert concentration["SUP-001"] == pytest.approx(0.667, rel=0.01)
        assert concentration["SUP-002"] == pytest.approx(0.333, rel=0.01)
    
    def test_calculate_supplier_concentration_empty_allocations(self):
        """Test concentration calculation with empty allocations."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        concentration = client.calculate_supplier_concentration([])
        
        assert concentration == {}
    
    def test_calculate_supplier_concentration_zero_quantity(self):
        """Test concentration calculation with zero total quantity."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        allocations = [
            {"supplier_id": "SUP-001", "quantity": 0}
        ]
        
        concentration = client.calculate_supplier_concentration(allocations)
        
        assert concentration == {}
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_find_risk_correlated_suppliers_success(self, mock_gremlin_client):
        """Test finding risk-correlated suppliers."""
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        mock_result = Mock()
        mock_result.all.return_value.result.return_value = [
            "SUP-002",
            "SUP-003"
        ]
        mock_client_instance.submit.return_value = mock_result
        
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        results = client.find_risk_correlated_suppliers("SUP-001")
        
        assert len(results) == 2
        assert "SUP-002" in results
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_find_risk_correlated_suppliers_empty_supplier_id(self, mock_gremlin_client):
        """Test validation for empty supplier ID."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        with pytest.raises(ValueError, match="supplier_id cannot be empty"):
            client.find_risk_correlated_suppliers("")
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_close_connection(self, mock_gremlin_client):
        """Test closing Neptune connection."""
        mock_client_instance = Mock()
        mock_gremlin_client.return_value = mock_client_instance
        
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        # Create connection
        client._get_client()
        
        # Close connection
        client.close()
        
        mock_client_instance.close.assert_called_once()
        assert client._client is None
    
    @patch("data.neptune_client.gremlin_client.Client")
    def test_close_without_connection(self, mock_gremlin_client):
        """Test closing when no connection exists."""
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )
        
        # Should not raise error
        client.close()
        
        assert client._client is None
