"""Shared pytest fixtures for the backend test suite."""

import sys
from pathlib import Path

import pytest

# Ensure the backend package root is on sys.path so imports work
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def sap_client_config() -> dict:
    """Dummy SAP client configuration for unit tests."""
    return {
        "base_url": "https://test-sap:44300/sap/opu/odata/sap",
        "username": "TEST_USER",
        "password": "TEST_PASS",
        "sap_client": "100",
    }
