"""
Integration tests for Lambda tools.

Uses moto for AWS service mocking.
Follows CDE standards: 70%+ coverage target.
"""

import pytest
import json
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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
from aws.lambda_tools import optimization_tool, explainability_tool, data_access_tool


class TestOptimizationTool:
    """Test suite for optimization Lambda tool."""
    
    @pytest.mark.integration
    @_skip_no_lambda_data
    def test_lambda_handler_success(self):
        """Test successful optimization."""
        event = {
            "materials": [
                {"material_id": "MAT-001", "quantity": 100}
            ],
            "constraints": {
                "max_supplier_concentration": 0.40,
                "max_lead_time_days": 45,
                "budget_max": 1000000
            },
            "objectives": {
                "cost": 0.4,
                "risk": 0.3,
                "lead_time": 0.3
            }
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = optimization_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "solutions" in body
        assert len(body["solutions"]) > 0
        assert body["request_id"] == "test-request-123"
    
    def test_lambda_handler_empty_materials(self):
        """Test validation error for empty materials."""
        event = {
            "materials": [],
            "constraints": {},
            "objectives": {}
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = optimization_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
        assert "materials" in body["error"].lower()
    
    def test_lambda_handler_missing_materials(self):
        """Test validation error for missing materials key."""
        event = {
            "constraints": {},
            "objectives": {}
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = optimization_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
    
    def test_lambda_handler_exception(self):
        """Test error handling for unexpected exceptions."""
        event = {
            "materials": [{"material_id": "MAT-001", "quantity": 100}]
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        with patch("aws.lambda_tools.optimization_tool._run_optimization") as mock_opt:
            mock_opt.side_effect = Exception("Unexpected error")
            
            result = optimization_tool.lambda_handler(event, context)
            
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "error" in body


class TestExplainabilityTool:
    """Test suite for explainability Lambda tool."""
    
    def test_lambda_handler_budget_solution(self):
        """Test explanation for budget solution."""
        event = {
            "solution_name": "Budget",
            "total_cost": 650000,
            "risk_score": 7.5,
            "quality_score": 6.5,
            "allocations": [
                {
                    "supplier_id": "SUP-001",
                    "material_id": "MAT-001",
                    "quantity": 100
                }
            ]
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = explainability_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "explanation" in body
        assert "Budget" in body["explanation"]
        assert "cost minimization" in body["explanation"].lower()
    
    def test_lambda_handler_balanced_solution(self):
        """Test explanation for balanced solution."""
        event = {
            "solution_name": "Balanced",
            "total_cost": 875000,
            "risk_score": 3.5,
            "quality_score": 8.2,
            "allocations": [
                {"supplier_id": "SUP-001"},
                {"supplier_id": "SUP-002"}
            ]
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = explainability_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "Balanced" in body["explanation"]
        assert "optimal balance" in body["explanation"].lower()
    
    def test_lambda_handler_premium_solution(self):
        """Test explanation for premium solution."""
        event = {
            "solution_name": "Premium",
            "total_cost": 1200000,
            "risk_score": 1.5,
            "quality_score": 9.5,
            "allocations": [
                {"supplier_id": "SUP-003"}
            ]
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = explainability_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "Premium" in body["explanation"]
        assert "quality" in body["explanation"].lower()
    
    def test_lambda_handler_missing_solution_name(self):
        """Test validation error for missing solution name."""
        event = {
            "total_cost": 100000,
            "risk_score": 5.0,
            "quality_score": 7.0,
            "allocations": []
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = explainability_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
    
    def test_generate_explanation_with_diversification(self):
        """Test explanation includes diversification insight."""
        explanation = explainability_tool._generate_explanation(
            "Balanced",
            875000,
            3.5,
            8.2,
            [
                {"supplier_id": "SUP-001"},
                {"supplier_id": "SUP-002"}
            ]
        )
        
        assert "diversification" in explanation.lower()
        assert "2 supplier" in explanation


class TestDataAccessTool:
    """Test suite for data access Lambda tool."""
    
    @_skip_no_neptune
    def test_lambda_handler_find_alternative_suppliers(self):
        """Test finding alternative suppliers."""
        event = {
            "query_type": "find_alternative_suppliers",
            "material_id": "MAT-001",
            "max_hops": 2
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "material_id" in body
        assert "alternative_suppliers" in body
        assert len(body["alternative_suppliers"]) > 0
    
    @_skip_no_neptune
    def test_lambda_handler_get_supplier_details(self):
        """Test getting supplier details."""
        event = {
            "query_type": "get_supplier_details",
            "supplier_id": "SUP-001"
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "supplier_id" in body
        assert "name" in body
        assert "rating" in body
    
    def test_lambda_handler_get_material_specifications(self):
        """Test getting material specifications — query type was removed, should return 400."""
        event = {
            "query_type": "get_material_specifications",
            "material_id": "MAT-001"
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
    
    def test_lambda_handler_missing_query_type(self):
        """Test validation error for missing query type."""
        event = {
            "material_id": "MAT-001"
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
    
    def test_lambda_handler_unknown_query_type(self):
        """Test validation error for unknown query type."""
        event = {
            "query_type": "unknown_query",
            "material_id": "MAT-001"
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Unknown query_type" in body["error"] or "Invalid query_type" in body["error"]
    
    def test_find_alternative_suppliers_missing_material_id(self):
        """Test validation for missing material ID."""
        event = {
            "query_type": "find_alternative_suppliers",
            "max_hops": 2
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
    
    def test_get_supplier_details_missing_supplier_id(self):
        """Test validation for missing supplier ID."""
        event = {
            "query_type": "get_supplier_details"
        }
        
        context = Mock()
        context.request_id = "test-request-123"
        
        result = data_access_tool.lambda_handler(event, context)
        
        assert result["statusCode"] == 400
