"""
Fixtures compartidos para los tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP para tests de API (usa httpx internamente)."""
    return TestClient(app)
