"""
Tests de API: endpoints raíz (/, /config, /health).
"""
import pytest
from fastapi.testclient import TestClient


def test_root_returns_online(client: TestClient):
    """GET / debe retornar status online."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "online"
    assert "app" in data
    assert "version" in data


def test_config_returns_iva(client: TestClient):
    """GET /config debe retornar configuración pública (IVA)."""
    r = client.get("/config")
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
