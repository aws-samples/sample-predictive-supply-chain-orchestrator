"""Unit tests for agentcore_bundle.main pure helpers (JWT actor + text extract)."""

import base64
import json
import os
import sys

import pytest

# The bundle is a self-contained deployment dir, not part of the api package.
_BUNDLE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "agentcore_bundle"
)
if _BUNDLE_DIR not in sys.path:
    sys.path.insert(0, _BUNDLE_DIR)

main = pytest.importorskip("main")


def _make_jwt(claims: dict) -> str:
    """Build an unsigned 3-segment JWT with the given payload claims."""
    payload = (
        base64.urlsafe_b64encode(json.dumps(claims).encode())
        .rstrip(b"=")
        .decode()
    )
    return f"header.{payload}.signature"


class _FakeResponse:
    def __init__(self, content):
        self.message = {"content": content}


@pytest.mark.unit
class TestActorFromJwt:
    def test_empty_header_is_anonymous(self):
        assert main._actor_from_jwt("") == "anonymous"

    def test_extracts_sub_with_bearer_prefix(self):
        token = "Bearer " + _make_jwt({"sub": "user-123"})
        assert main._actor_from_jwt(token) == "user-123"

    def test_extracts_sub_without_bearer_prefix(self):
        assert main._actor_from_jwt(_make_jwt({"sub": "abc"})) == "abc"

    def test_missing_sub_is_anonymous(self):
        assert main._actor_from_jwt("Bearer " + _make_jwt({})) == "anonymous"

    def test_malformed_token_is_anonymous(self):
        assert main._actor_from_jwt("Bearer not-a-jwt") == "anonymous"

    def test_bad_base64_is_anonymous(self):
        assert main._actor_from_jwt("Bearer a.@@@.c") == "anonymous"


@pytest.mark.unit
class TestExtractText:
    def test_concatenates_text_blocks(self):
        resp = _FakeResponse([{"text": "a"}, {"toolUse": {}}, {"text": "b"}])
        assert main._extract_text(resp) == "ab"

    def test_no_text_blocks_returns_empty(self):
        assert main._extract_text(_FakeResponse([{"toolUse": {}}])) == ""

    def test_empty_content_returns_empty(self):
        assert main._extract_text(_FakeResponse([])) == ""
