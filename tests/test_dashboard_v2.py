"""
Tests Dashboard V2 — Fase 1 backend.

Cubre scoring, recomendación única, agrupación, secciones enum, lazy real y TZ citas.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from app.routers.dashboard_agregado import parse_secciones
from app.routers.dashboard_operativa import (
    CandidatoOperativo,
    _extraer_candidatos_citas,
    calcular_decision_score,
    construir_prioridades_agrupadas,
    seleccionar_recomendacion_inteligente,
)
from app.utils.fechas import ahora_local
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"DashV2 {rol}",
        email=f"dashv2_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("DashV2Secret!9"),
        rol=rol,
        activo=True,
    )
    session.add(usuario)
    session.flush()
    token = create_access_token(data={"sub": str(usuario.id_usuario), "rol": rol})
    return usuario, token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Unitarios sin BD ---


def test_scoring_antiguedad_item_mas_antiguo_gana():
    base = dict(
        grupo="cobros",
        item_id="a",
        titulo="t",
        subtitulo=None,
        to="/operaciones/caja",
        referencia=None,
        impacto_monto=1000.0,
    )
    joven = CandidatoOperativo(**base, minutos_antiguedad=10.0)
    viejo = CandidatoOperativo(**base, minutos_antiguedad=300.0)
    assert calcular_decision_score(viejo) > calcular_decision_score(joven)


def test_una_sola_recomendacion_estable_sin_candidatos():
    rec = seleccionar_recomendacion_inteligente([])
    assert rec["severidad"] == "estable"
    assert rec["titulo"]


def test_una_sola_recomendacion_con_candidatos():
    candidatos = [
        CandidatoOperativo(
            grupo="cobros",
            item_id="ot-1",
            titulo="A",
            subtitulo=None,
            to="/operaciones/caja",
            referencia={"tipo": "orden_trabajo", "id": 1},
            minutos_antiguedad=400.0,
            impacto_monto=5000.0,
        ),
        CandidatoOperativo(
            grupo="citas",
            item_id="cita-1",
            titulo="B",
            subtitulo=None,
            to="/operaciones/recepcion",
            referencia={"tipo": "cita", "id": 1},
            minutos_antiguedad=5.0,
        ),
    ]
    rec = seleccionar_recomendacion_inteligente(candidatos)
    assert isinstance(rec, dict)
    assert "titulo" in rec and "decision_score" in rec


def test_agrupacion_por_familia_max_tres_items():
    candidatos = [
        CandidatoOperativo(
            grupo="cobros",
            item_id=f"ot-{i}",
            titulo=f"OT {i}",
            subtitulo=None,
            to="/operaciones/caja",
            referencia=None,
            minutos_antiguedad=60.0 * i,
            impacto_monto=100.0 * i,
        )
        for i in range(1, 6)
    ]
    grupos = construir_prioridades_agrupadas(candidatos)
    assert len(grupos) == 1
    assert grupos[0]["grupo"] == "cobros"
    assert grupos[0]["total"] == 5
    assert len(grupos[0]["items"]) == 3
    assert "ver_todas" in grupos[0]


def test_parse_secciones_default_operativa():
    assert parse_secciones(None) == ["operativa"]
    assert parse_secciones("") == ["operativa"]


def test_parse_secciones_invalidas_raises():
    with pytest.raises(ValueError, match="inválidas"):
        parse_secciones("operativa,foo")


# --- API ---


def test_api_secciones_invalidas_422(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get(
        "/api/dashboard?secciones=invalida",
        headers=_auth(token),
    )
    assert r.status_code == 422


def test_api_default_operativa_con_recomendacion(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get("/api/dashboard", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["secciones_calculadas"] == ["operativa"]
    assert data["operativa"] is not None
    assert "recomendacion_inteligente" in data["operativa"]
    assert data["finanzas"] is None
    assert data["inventario"] is None


@patch("app.routers.dashboard_agregado._build_finanzas")
@patch("app.routers.dashboard_agregado.InventarioService.calcular_valor_inventario")
def test_lazy_no_finanzas_ni_inventario_en_default(
    mock_valor_inv,
    mock_build_finanzas,
    client_transactional_db,
    db_session_transactional,
):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get("/api/dashboard", headers=_auth(token))
    assert r.status_code == 200
    mock_valor_inv.assert_not_called()
    mock_build_finanzas.assert_not_called()


@patch("app.routers.dashboard_agregado._build_inventario")
def test_inventario_solo_si_solicitado(
    mock_build_inventario,
    client_transactional_db,
    db_session_transactional,
):
    mock_build_inventario.return_value = {"valor_inventario": 0}
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    client_transactional_db.get("/api/dashboard", headers=_auth(token))
    mock_build_inventario.assert_not_called()

    client_transactional_db.get("/api/dashboard?secciones=inventario", headers=_auth(token))
    mock_build_inventario.assert_called_once()


@patch("app.routers.dashboard_agregado._build_finanzas")
def test_finanzas_solo_si_solicitado(
    mock_build_finanzas,
    client_transactional_db,
    db_session_transactional,
):
    mock_build_finanzas.return_value = {"periodo": "mes", "utilidad_neta": 0}
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    client_transactional_db.get("/api/dashboard", headers=_auth(token))
    mock_build_finanzas.assert_not_called()

    client_transactional_db.get(
        "/api/dashboard?secciones=finanzas&periodo=mes",
        headers=_auth(token),
    )
    mock_build_finanzas.assert_called_once()


def test_cita_proxima_usa_hora_local_taller(db_session_transactional):
    from app.models.cita import Cita, EstadoCita
    from app.models.cliente import Cliente

    uid = uuid.uuid4().hex[:8]
    cliente = Cliente(nombre=f"Cita TZ {uid}", telefono="6441234567")
    db_session_transactional.add(cliente)
    db_session_transactional.flush()

    en_dos_horas = ahora_local() + timedelta(hours=2)
    cita = Cita(
        id_cliente=cliente.id_cliente,
        fecha_hora=en_dos_horas,
        estado=EstadoCita.CONFIRMADA,
        motivo="Prueba TZ dashboard",
    )
    db_session_transactional.add(cita)
    db_session_transactional.flush()

    candidatos = _extraer_candidatos_citas(db_session_transactional)
    proximos = [c for c in candidatos if c.item_id == f"cita-{cita.id_cita}"]
    assert len(proximos) == 1
    assert proximos[0].minutos_proximidad is not None
    assert 110 <= proximos[0].minutos_proximidad <= 130
