"""Tests de utilidades de teléfono de clientes."""

from unittest.mock import MagicMock

from app.models.cliente import Cliente
from app.utils.cliente_telefono import buscar_cliente_por_telefono, normalizar_telefono


def test_normalizar_telefono_formatos():
    assert normalizar_telefono("644 123 4567") == "6441234567"
    assert normalizar_telefono("+52 644 123 4567") == "6441234567"
    assert normalizar_telefono("644-123-4567") == "6441234567"
    assert normalizar_telefono("") is None
    assert normalizar_telefono(None) is None


def test_buscar_cliente_por_telefono():
    c1 = Cliente(id_cliente=1, nombre="Juan Pérez", telefono="644-111-2233")
    c2 = Cliente(id_cliente=2, nombre="María López", telefono="6442223344")

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [c1, c2]

    encontrado = buscar_cliente_por_telefono(db, "644 111 2233")
    assert encontrado is not None
    assert encontrado.id_cliente == 1

    assert buscar_cliente_por_telefono(db, "6442223344").id_cliente == 2
    assert buscar_cliente_por_telefono(db, "9999999999") is None

    db.query.return_value.filter.return_value.filter.return_value.all.return_value = [c2]
    assert buscar_cliente_por_telefono(db, "6441112233", excluir_id=1) is None
