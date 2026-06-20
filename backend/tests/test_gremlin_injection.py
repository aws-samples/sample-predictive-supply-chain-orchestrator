"""
Security tests: Gremlin injection prevention in Neptune ID validation.

Verifies that vertex/edge IDs interpolated into Gremlin queries are
validated against an allowlist (alphanumeric + hyphen + underscore),
rejecting injection payloads before they reach the database.
"""

import pytest

from data.neptune_client import _validate_graph_id


class TestGraphIdValidation:
    """Validation helper used at every Gremlin interpolation site."""

    @pytest.mark.parametrize("valid_id", [
        "SUP-001",
        "MAT-BAT-001",
        "MAT_BAT_001",
        "supplier123",
        "ABC",
    ])
    def test_accepts_valid_ids(self, valid_id):
        assert _validate_graph_id(valid_id, "supplier_id") == valid_id

    @pytest.mark.parametrize("malicious_id", [
        "SUP-001').drop().V('",            # chained mutating traversal
        "SUP-001').V().drop(",             # drop entire graph
        "x') ; g.V().drop(); ('",          # statement separator
        "SUP-001'}}",                       # brace escape
        "'+g.V()+'",                        # concatenation
        "SUP 001",                          # space
        "SUP/001",                          # slash
        "../etc",                           # path-ish
        'SUP"001',                          # double quote
    ])
    def test_rejects_injection_payloads(self, malicious_id):
        with pytest.raises(ValueError, match="Invalid supplier_id"):
            _validate_graph_id(malicious_id, "supplier_id")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_graph_id("", "supplier_id")

    def test_error_message_uses_field_name(self):
        with pytest.raises(ValueError, match="material_id"):
            _validate_graph_id("bad id", "material_id")
