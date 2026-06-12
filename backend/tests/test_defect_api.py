"""
Integration tests for defect tracking API endpoints.

Tests GET /api/defects, GET /api/defects/summary,
POST /api/defects/<id>/recall, GET /api/defects/report.
"""

import pytest
import json

from api.server import app


class TestGetDefects:
    """Test GET /api/defects endpoint."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_get_all_defects(self, client):
        response = client.get("/api/defects")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "defects" in data
        assert "total" in data
        assert data["total"] == 20
        assert len(data["defects"]) == 20

    def test_defect_record_structure(self, client):
        response = client.get("/api/defects")
        data = json.loads(response.data)
        defect = data["defects"][0]
        required_fields = [
            "defect_id", "supplier_id", "supplier_name",
            "material_id", "material_name", "defect_date",
            "severity", "category", "quantity_affected",
            "batch_id", "description", "root_cause",
            "status", "recall_initiated",
        ]
        for field in required_fields:
            assert field in defect, f"Missing field: {field}"

    def test_defects_sorted_by_date_desc(self, client):
        response = client.get("/api/defects")
        data = json.loads(response.data)
        dates = [d["defect_date"] for d in data["defects"]]
        assert dates == sorted(dates, reverse=True)

    def test_filter_by_supplier(self, client):
        response = client.get("/api/defects?supplier_id=SUP-001")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] > 0
        for d in data["defects"]:
            assert d["supplier_id"] == "SUP-001"

    def test_filter_by_material(self, client):
        response = client.get("/api/defects?material_id=MAT-BAT-001")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] > 0
        for d in data["defects"]:
            assert d["material_id"] == "MAT-BAT-001"

    def test_filter_by_severity(self, client):
        response = client.get("/api/defects?severity=CRITICAL")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] > 0
        for d in data["defects"]:
            assert d["severity"] == "CRITICAL"

    def test_filter_by_severity_case_insensitive(self, client):
        response = client.get("/api/defects?severity=critical")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] > 0
        for d in data["defects"]:
            assert d["severity"] == "CRITICAL"

    def test_filter_by_status(self, client):
        response = client.get("/api/defects?status=OPEN")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] > 0
        for d in data["defects"]:
            assert d["status"] == "OPEN"

    def test_filter_combined(self, client):
        response = client.get("/api/defects?severity=CRITICAL&status=OPEN")
        assert response.status_code == 200
        data = json.loads(response.data)
        for d in data["defects"]:
            assert d["severity"] == "CRITICAL"
            assert d["status"] == "OPEN"

    def test_filter_no_results(self, client):
        response = client.get("/api/defects?supplier_id=SUP-999")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["total"] == 0
        assert data["defects"] == []

    def test_filter_invalid_severity_rejected(self, client):
        response = client.get("/api/defects?severity=INVALID")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_filter_invalid_status_rejected(self, client):
        response = client.get("/api/defects?status=INVALID")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_supplier_name_enriched(self, client):
        response = client.get("/api/defects?supplier_id=SUP-001")
        data = json.loads(response.data)
        if data["total"] > 0:
            # All defects for SUP-001 should have the enriched supplier name
            for d in data["defects"]:
                assert d["supplier_name"] != "", "supplier_name should be enriched"
                assert d["supplier_name"] != d["supplier_id"], "supplier_name should not be the raw ID"

    def test_material_name_enriched(self, client):
        response = client.get("/api/defects?material_id=MAT-BAT-001")
        data = json.loads(response.data)
        if data["total"] > 0:
            assert "Battery" in data["defects"][0]["material_name"]


class TestDefectSummary:
    """Test GET /api/defects/summary endpoint."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_summary_success(self, client):
        response = client.get("/api/defects/summary")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "overview" in data
        assert "by_severity" in data
        assert "by_supplier" in data
        assert "by_material" in data
        assert "by_category" in data

    def test_summary_overview_fields(self, client):
        response = client.get("/api/defects/summary")
        data = json.loads(response.data)
        overview = data["overview"]
        assert overview["total_defects"] == 20
        assert overview["open_defects"] >= 0
        assert overview["resolved_defects"] >= 0
        assert overview["recalls_initiated"] >= 0
        assert overview["critical_defects"] >= 0
        assert overview["total_units_affected"] > 0

    def test_summary_overview_counts_consistent(self, client):
        response = client.get("/api/defects/summary")
        data = json.loads(response.data)
        overview = data["overview"]
        # open + resolved + closed should roughly equal total
        # (closed defects may exist too)
        assert overview["open_defects"] <= overview["total_defects"]
        assert overview["resolved_defects"] <= overview["total_defects"]
        assert overview["critical_defects"] <= overview["total_defects"]

    def test_summary_by_severity(self, client):
        response = client.get("/api/defects/summary")
        data = json.loads(response.data)
        by_sev = data["by_severity"]
        assert "CRITICAL" in by_sev
        assert "MAJOR" in by_sev
        assert "MINOR" in by_sev
        total_from_severity = sum(v["count"] for v in by_sev.values())
        assert total_from_severity == data["overview"]["total_defects"]

    def test_summary_by_supplier_has_defect_score(self, client):
        response = client.get("/api/defects/summary")
        data = json.loads(response.data)
        for sid, info in data["by_supplier"].items():
            assert "supplier_name" in info
            assert "total_defects" in info
            assert "defect_score" in info
            assert 0 <= info["defect_score"] <= 10

    def test_summary_by_material_has_suppliers_affected(self, client):
        response = client.get("/api/defects/summary")
        data = json.loads(response.data)
        for mid, info in data["by_material"].items():
            assert "material_name" in info
            assert "suppliers_affected" in info
            assert isinstance(info["suppliers_affected"], list)

    def test_summary_by_category(self, client):
        response = client.get("/api/defects/summary")
        data = json.loads(response.data)
        categories = data["by_category"]
        assert len(categories) > 0
        total_from_categories = sum(categories.values())
        assert total_from_categories == data["overview"]["total_defects"]


class TestInitiateRecall:
    """Test POST /api/defects/<id>/recall endpoint."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_recall_success(self, client):
        response = client.post("/api/defects/DEF-001/recall")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "recall_id" in data
        assert data["recall_id"].startswith("RCL-")
        assert data["defect_id"] == "DEF-001"
        assert data["status"] == "RECALL_INITIATED"
        assert "initiated_at" in data
        assert "message" in data

    def test_recall_includes_defect_details(self, client):
        response = client.post("/api/defects/DEF-001/recall")
        data = json.loads(response.data)
        assert "supplier_id" in data
        assert "supplier_name" in data
        assert "material_id" in data
        assert "material_name" in data
        assert "batch_id" in data
        assert "quantity_affected" in data
        assert data["quantity_affected"] > 0

    def test_recall_not_found(self, client):
        response = client.post("/api/defects/DEF-999/recall")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_recall_invalid_id_format(self, client):
        response = client.post("/api/defects/INVALID-ID/recall")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Invalid defect ID" in data["error"]

    def test_recall_xss_in_id_rejected(self, client):
        response = client.post("/api/defects/<script>alert(1)</script>/recall")
        assert response.status_code == 404  # Flask won't match the route with special chars

    def test_recall_generates_unique_ids(self, client):
        r1 = client.post("/api/defects/DEF-001/recall")
        r2 = client.post("/api/defects/DEF-002/recall")
        d1 = json.loads(r1.data)
        d2 = json.loads(r2.data)
        assert d1["recall_id"] != d2["recall_id"]


class TestDefectReport:
    """Test GET /api/defects/report endpoint."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_report_all_defects(self, client):
        response = client.get("/api/defects/report")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "report" in data
        report = data["report"]
        assert report["total_defects"] == 20
        assert "avg_resolution_days" in report
        assert "monthly_trend" in report
        assert "top_root_causes" in report
        assert "recall_rate" in report
        assert "open_rate" in report

    def test_report_monthly_trend_sorted(self, client):
        response = client.get("/api/defects/report")
        data = json.loads(response.data)
        months = list(data["report"]["monthly_trend"].keys())
        assert months == sorted(months)

    def test_report_monthly_trend_structure(self, client):
        response = client.get("/api/defects/report")
        data = json.loads(response.data)
        for month, info in data["report"]["monthly_trend"].items():
            assert "total" in info
            assert "critical" in info
            assert "quantity" in info
            assert info["total"] > 0
            assert info["critical"] >= 0

    def test_report_top_root_causes(self, client):
        response = client.get("/api/defects/report")
        data = json.loads(response.data)
        causes = data["report"]["top_root_causes"]
        assert len(causes) > 0
        assert len(causes) <= 5
        for rc in causes:
            assert "cause" in rc
            assert "count" in rc
            assert rc["count"] > 0
        # Should be sorted by count descending
        counts = [rc["count"] for rc in causes]
        assert counts == sorted(counts, reverse=True)

    def test_report_rates_valid(self, client):
        response = client.get("/api/defects/report")
        data = json.loads(response.data)
        report = data["report"]
        assert 0 <= report["recall_rate"] <= 100
        assert 0 <= report["open_rate"] <= 100

    def test_report_filtered_by_supplier(self, client):
        response = client.get("/api/defects/report?supplier_id=SUP-001")
        assert response.status_code == 200
        data = json.loads(response.data)
        report = data["report"]
        assert report["total_defects"] > 0
        assert report["total_defects"] < 20  # Should be fewer than all

    def test_report_no_defects_for_supplier(self, client):
        response = client.get("/api/defects/report?supplier_id=SUP-999")
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should return a message, not crash
        assert "report" in data

    def test_report_avg_resolution_days(self, client):
        response = client.get("/api/defects/report")
        data = json.loads(response.data)
        avg = data["report"]["avg_resolution_days"]
        if avg is not None:
            assert avg > 0
