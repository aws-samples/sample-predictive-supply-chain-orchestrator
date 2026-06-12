"""
Unit tests for Flask API endpoints.

Tests health check, optimization endpoint, error handling.
Target: 70%+ coverage.
"""

import pytest
import json
from unittest.mock import Mock, patch

from api.server import app
from core.models import OptimizationRequest, MaterialDemand


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'environment' in data


class TestOptimizeEndpoint:
    """Test optimization endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_optimize_success(self, client):
        """Test successful optimization."""
        request_data = {
            "materials": [
                {
                    "material_id": "MAT-BAT-001",
                    "quantity": 500
                }
            ],
            "constraints": {
                "max_supplier_concentration": 0.40,
                "max_lead_time_days": 45,
                "budget_max": 1000000,
                "budget_min": 0
            },
            "objectives": {
                "cost": 0.4,
                "risk": 0.3,
                "lead_time": 0.3
            }
        }
        
        response = client.post(
            '/api/optimize',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'solutions' in data
        assert 'request_id' in data
        assert 'computation_time_ms' in data
        assert len(data['solutions']) >= 3

    def test_optimize_invalid_json(self, client):
        """Test optimization with invalid JSON."""
        response = client.post(
            '/api/optimize',
            data='invalid json',
            content_type='application/json'
        )
        
        # Flask returns 500 for JSON decode errors, not 400
        assert response.status_code == 500

    def test_optimize_missing_materials(self, client):
        """Test optimization with missing materials."""
        request_data = {
            "constraints": {
                "max_supplier_concentration": 0.40
            }
        }
        
        response = client.post(
            '/api/optimize',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400

    def test_optimize_invalid_material_id(self, client):
        """Test optimization with non-existent material."""
        request_data = {
            "materials": [
                {
                    "material_id": "MAT-999-999",
                    "quantity": 100
                }
            ]
        }
        
        response = client.post(
            '/api/optimize',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_optimize_quantity_below_moq(self, client):
        """Test optimization with quantity below MOQ."""
        request_data = {
            "materials": [
                {
                    "material_id": "MAT-BAT-001",
                    "quantity": 10  # Below MOQ
                }
            ]
        }
        
        response = client.post(
            '/api/optimize',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestDataEndpoints:
    """Test data access endpoints."""

    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_get_suppliers(self, client):
        response = client.get('/api/suppliers')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'suppliers' in data
        assert len(data['suppliers']) > 0

    def test_get_materials(self, client):
        response = client.get('/api/materials')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'materials' in data
        assert len(data['materials']) > 0

    def test_get_supplier_materials(self, client):
        response = client.get('/api/supplier-materials')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'supplier_materials' in data

    def test_get_supplier_materials_filtered(self, client):
        response = client.get('/api/supplier-materials?supplier_id=SUP-001')
        assert response.status_code == 200
        data = json.loads(response.data)
        for sm in data['supplier_materials']:
            assert sm['supplier_id'] == 'SUP-001'

    def test_get_volume_tiers(self, client):
        response = client.get('/api/volume-tiers')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'volume_tiers' in data

    def test_get_supplier_performance(self, client):
        response = client.get('/api/supplier-performance')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'performance' in data
        assert len(data['performance']) > 0

    def test_get_supplier_performance_filtered(self, client):
        response = client.get('/api/supplier-performance?supplier_id=SUP-001')
        assert response.status_code == 200
        data = json.loads(response.data)
        for p in data['performance']:
            assert p['supplier_id'] == 'SUP-001'


class TestPurchaseRequisitions:
    """Test purchase requisition endpoints."""

    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_create_pr_success(self, client):
        pr_data = {
            "solution_name": "Balanced",
            "allocations": [
                {"supplier_id": "SUP-001", "material_id": "MAT-BAT-001", "quantity": 500, "unit_price": 280.0},
                {"supplier_id": "SUP-002", "material_id": "MAT-MOT-001", "quantity": 500, "unit_price": 45.0},
            ],
            "requester": "test@voltcycle.com",
            "notes": "Test PR"
        }
        response = client.post(
            '/api/purchase-requisitions',
            data=json.dumps(pr_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'pr_ids' in data
        assert data['total_prs'] == 2
        assert data['total_value'] == 500 * 280.0 + 500 * 45.0
        assert data['status'] == 'pending_approval'

    def test_create_pr_missing_fields(self, client):
        response = client.post(
            '/api/purchase-requisitions',
            data=json.dumps({"solution_name": "Budget"}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_list_prs(self, client):
        response = client.get('/api/purchase-requisitions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'purchase_requisitions' in data
        assert 'total' in data

    def test_approve_pr(self, client):
        response = client.post(
            '/api/purchase-requisitions/PR-2026-001/approve',
            data=json.dumps({"approver": "manager@voltcycle.com"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'approved'


class TestChatEndpoint:
    """Test chat endpoint."""

    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_chat_success(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "help"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert len(data['response']) > 0

    def test_chat_optimize(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "optimize for 500 e-bikes"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert 'solution' in data['response'].lower() or 'optim' in data['response'].lower()

    def test_chat_missing_message(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_chat_explain(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "explain the Balanced solution"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data

    def test_chat_risk(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "analyze supply chain risk"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data

    def test_chat_suppliers(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "show supplier data"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data

    def test_chat_defects(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "show me defects"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert 'defect' in data['response'].lower()

    def test_chat_defects_for_supplier(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "defects for SUP-001"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        assert 'defect' in data['response'].lower() or 'score' in data['response'].lower()

    def test_chat_how_many_open_defects(self, client):
        """The exact query the user reported as broken."""
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "How many defect cases are currently open?"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data
        resp = data['response'].lower()
        assert 'open' in resp
        # Should give a direct answer with the number
        assert '7' in data['response']

    def test_chat_compare(self, client):
        response = client.post(
            '/api/chat',
            data=json.dumps({"message": "compare solutions"}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'response' in data


class TestErrorHandlers:
    """Test error handlers."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_404_not_found(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()
