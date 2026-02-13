"""
Tests de API: endpoints raíz (/, /config, /health).
"""
import pytest
from fastapi.testclient import TestClient


def test_root_returns_online(client: TestClient):
    """GET /api/ debe retornar status online (JSON)."""
    r = client.get("/api/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "online"
    assert "app" in data
    assert "version" in data


def test_config_returns_iva(client: TestClient):
    """GET /api/config debe retornar configuración pública (IVA)."""
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "iva_porcentaje" in data


def test_health_returns_valid_status(client: TestClient):
    """GET /health debe retornar status (healthy o unhealthy según conexión BD)."""
    r = client.get("/health")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "status" in data
    assert "database" in data
    assert data["status"] in ("healthy", "unhealthy")


def test_openapi_json_available(client: TestClient):
    """GET /openapi.json debe estar disponible cuando docs están habilitados."""
    r = client.get("/openapi.json")
    # 200 si docs habilitados; 404 si deshabilitados
    if r.status_code == 200:
        data = r.json()
        assert "openapi" in data
        assert "paths" in data
