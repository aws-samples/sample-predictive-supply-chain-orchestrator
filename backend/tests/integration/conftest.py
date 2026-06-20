"""Shared fixtures / path setup for integration tests.

Adds the backend package root to sys.path once so integration test modules
can import `aws.lambda_tools.*`, `data.*`, etc. without per-file path hacks.
"""

import os
import sys

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)
