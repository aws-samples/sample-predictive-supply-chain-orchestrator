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


def _gv(value):
    """Wrap a Python value as the GraphSON typed value the parser expects."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return {"@type": "g:Int64", "@value": value}
    if isinstance(value, float):
        return {"@type": "g:Double", "@value": value}
    return value


def _vertex_map(props):
    """Build a GraphSON g:Map mirroring Neptune's elementMap() output.

    elementMap() emits a flat [key, value, key, value, ...] list where the
    id key is a g:T token. The NeptuneClient parser resolves g:T -> "id".
    """
    flat = []
    for key, value in props.items():
        if key == "id":
            flat.append({"@type": "g:T", "@value": "id"})
        else:
            flat.append(key)
        flat.append(_gv(value))
    return {"@type": "g:Map", "@value": flat}


def _graphson_list(items):
    """Wrap vertex/map entries in a GraphSON g:List (Neptune result.data)."""
    return {"@type": "g:List", "@value": items}


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
    
    @patch.object(NeptuneClient, "_http_query")
    def test_find_alternative_suppliers_success(self, mock_http_query):
        """Test finding alternative suppliers."""
        # Neptune HTTP elementMap() returns a GraphSON g:List of g:Map vertices.
        mock_http_query.return_value = _graphson_list([
            _vertex_map({
                "id": "SUP-002",
                "name": "Alternative Supplier",
                "location": "Shanghai, China",
                "rating": 4.5,
                "geopolitical_risk_score": 0.3,
            })
        ])

        # Test
        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )

        results = client.find_alternative_suppliers("MAT-001", max_hops=2)

        # Verify
        assert len(results) == 1
        assert results[0]["supplier_id"] == "SUP-002"
        assert results[0]["name"] == "Alternative Supplier"
        assert results[0]["rating"] == 4.5
        mock_http_query.assert_called_once()
    
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
    
    @patch.object(NeptuneClient, "_http_query")
    def test_find_alternative_suppliers_http_error(self, mock_http_query):
        """Test that HTTP query failures propagate out of the method."""
        # The HTTP-based implementation re-raises whatever _http_query raises.
        mock_http_query.side_effect = ConnectionError("Neptune unreachable")

        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )

        with pytest.raises(ConnectionError, match="Neptune unreachable"):
            client.find_alternative_suppliers("MAT-001")
    
    @patch.object(NeptuneClient, "_http_query")
    def test_get_supplier_network_success(self, mock_http_query):
        """Test getting supplier network."""
        # get_supplier_network runs a project('material','edge') traversal;
        # each result row is a g:Map with the projected keys.
        mock_http_query.return_value = _graphson_list([
            {
                "@type": "g:Map",
                "@value": [
                    "material",
                    _vertex_map({"id": "MAT-001", "name": "Test Material"}),
                    "edge",
                    _vertex_map({"base_price": 10.0, "lead_time_days": 5}),
                ],
            }
        ])

        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )

        result = client.get_supplier_network("SUP-001")

        assert result["supplier_id"] == "SUP-001"
        assert "relationships" in result
        assert len(result["relationships"]) == 1
        assert result["relationships"][0]["material"]["id"] == "MAT-001"
        mock_http_query.assert_called_once()
    
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
    
    @patch.object(NeptuneClient, "_http_query")
    def test_find_risk_correlated_suppliers_success(self, mock_http_query):
        """Test finding risk-correlated suppliers.

        find_risk_correlated_suppliers calls get_suppliers() (one _http_query
        returning all suppliers) then filters in Python by shared location words.
        SUP-002 and SUP-003 share the "China" region word with SUP-001; SUP-004
        is in the USA and must be excluded.
        """
        mock_http_query.return_value = _graphson_list([
            _vertex_map({"id": "SUP-001", "name": "Ref", "location": "Shanghai, China"}),
            _vertex_map({"id": "SUP-002", "name": "Alt A", "location": "Shenzhen, China"}),
            _vertex_map({"id": "SUP-003", "name": "Alt B", "location": "Beijing, China"}),
            _vertex_map({"id": "SUP-004", "name": "Other", "location": "Austin, USA"}),
        ])

        client = NeptuneClient(
            endpoint="test-cluster.us-east-1.neptune.amazonaws.com"
        )

        results = client.find_risk_correlated_suppliers("SUP-001")

        assert len(results) == 2
        assert "SUP-002" in results
        assert "SUP-003" in results
        assert "SUP-004" not in results
        assert "SUP-001" not in results
    
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
