"""
Evaluador financiero-operativo para la Capa A0 (P4.0).

Fuente única de evaluación para mutaciones financiero-operativas en bandejas A0.
No ejecuta mutaciones; refleja las mismas reglas que POST /api/pagos/ (turno, saldo).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.caja_turno import CajaTurno
from app.models.orden_trabajo import OrdenTrabajo
from app.models.pago import Pago
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.utils.liquidacion_pago import evaluar_pago_contra_total

SALDO_EPSILON = 0.001

ROLES_CAJA = frozenset({"ADMIN", "CAJA"})

ACCIONES_FINANCIERAS_ITEM_ONLY = (
    "registrar_pago",
    "crear_venta_desde_ot",
    "entregar_vehiculo",
)

MOTIVO_ITEM_ONLY: dict[str, str] = {
    "registrar_pago": "Disponible en ítems de bandeja Por cobrar o Ventas con saldo",
    "crear_venta_desde_ot": "Disponible en ítems de bandeja OT por cobrar",
    "entregar_vehiculo": "Disponible en ítems de bandeja OT listas para entrega",
}


@dataclass(frozen=True)
class AccionEvaluada:
    accion: str
    permitida: bool
    motivo_bloqueo: Optional[str] = None
    codigo_bloqueo: Optional[str] = None
    alcance: Optional[str] = None
    contexto: Optional[dict[str, Any]] = None


def _rol_usuario(usuario: Usuario) -> str:
    return usuario.rol.value if hasattr(usuario.rol, "value") else str(usuario.rol)


def _estado_orden(orden: OrdenTrabajo) -> str:
    return orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)


def _estado_venta(venta: Venta) -> str:
    return venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado)


def _accion(
    nombre: str,
    permitida: bool,
    motivo: Optional[str] = None,
    codigo: Optional[str] = None,
    *,
    alcance: Optional[str] = None,
    contexto: Optional[dict[str, Any]] = None,
) -> AccionEvaluada:
    return AccionEvaluada(
        accion=nombre,
        permitida=permitida,
        motivo_bloqueo=motivo if not permitida else None,
        codigo_bloqueo=codigo if not permitida else None,
        alcance=alcance,
        contexto=contexto if permitida else None,
    )


def venta_es_activa(venta: Optional[Venta]) -> bool:
    """Venta activa = estado distinto de CANCELADA (ADR §4)."""
    if venta is None:
        return False
    return _estado_venta(venta) != "CANCELADA"


def calcular_saldo_venta(db: Session, venta: Venta) -> float:
    """Mismo cálculo que operaciones_service / pagos: total - sum(pagos), mínimo 0."""
    total_pagado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .filter(Pago.id_venta == venta.id_venta)
        .scalar()
    )
    return max(0.0, float(venta.total) - float(total_pagado or 0))


def turno_abierto_usuario(db: Session, usuario: Usuario) -> Optional[CajaTurno]:
    """Misma consulta que app/routers/pagos.py — turno ABIERTO del usuario."""
    return (
        db.query(CajaTurno)
        .filter(
            CajaTurno.id_usuario == usuario.id_usuario,
            CajaTurno.estado == "ABIERTO",
        )
        .first()
    )


def _venta_activa_por_orden(db: Session, orden_id: int) -> Optional[Venta]:
    return (
        db.query(Venta)
        .filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA")
        .order_by(Venta.id_venta.desc())
        .first()
    )


def accion_global_item_only(accion: str) -> AccionEvaluada:
    """Política Opción A: mutación financiero-operativa nunca permitida en global."""
    motivo = MOTIVO_ITEM_ONLY.get(
        accion,
        "Disponible únicamente en acciones del ítem correspondiente",
    )
    return _accion(
        accion,
        False,
        motivo,
        "REQUIERE_CONTEXTO_ENTIDAD",
        alcance="item_only",
    )


def acciones_globales_financieras_item_only() -> list[AccionEvaluada]:
    return [accion_global_item_only(nombre) for nombre in ACCIONES_FINANCIERAS_ITEM_ONLY]


def accion_a_dict(evaluada: AccionEvaluada) -> dict[str, Any]:
    result: dict[str, Any] = {
        "accion": evaluada.accion,
        "permitida": evaluada.permitida,
        "motivo_bloqueo": evaluada.motivo_bloqueo,
    }
    if evaluada.codigo_bloqueo is not None:
        result["codigo_bloqueo"] = evaluada.codigo_bloqueo
    if evaluada.alcance is not None:
        result["alcance"] = evaluada.alcance
    if evaluada.contexto is not None:
        result["contexto"] = evaluada.contexto
    return result


def evaluar_registrar_pago(
    db: Session,
    venta: Optional[Venta],
    usuario: Usuario,
    *,
    monto: Optional[Decimal | float] = None,
) -> AccionEvaluada:
    """
    Reglas ADR §7 — alineadas con POST /api/pagos/ (turno, venta, saldo, excedente).
    """
    rol = _rol_usuario(usuario)
    if rol not in ROLES_CAJA:
        return _accion(
            "registrar_pago",
            False,
            f"Rol {rol} no puede registrar pagos",
            "ROL_NO_PERMITIDO",
        )

    if turno_abierto_usuario(db, usuario) is None:
        return _accion(
            "registrar_pago",
            False,
            "No puedes registrar pagos sin un turno de caja abierto",
            "TURNO_CERRADO",
        )

    if venta is None:
        return _accion(
            "registrar_pago",
            False,
            "La venta no existe",
            "VENTA_INEXISTENTE",
        )

    if not venta_es_activa(venta):
        return _accion(
            "registrar_pago",
            False,
            "La venta está cancelada",
            "VENTA_CANCELADA",
        )

    saldo = calcular_saldo_venta(db, venta)
    if saldo <= SALDO_EPSILON:
        return _accion(
            "registrar_pago",
            False,
            "La venta no tiene saldo pendiente",
            "SALDO_CERO",
        )

    if monto is not None:
        total_pagado = float(venta.total) - saldo
        excede, _, _, _, _ = evaluar_pago_contra_total(total_pagado, monto, venta.total)
        if excede:
            return _accion(
                "registrar_pago",
                False,
                "El pago excede el total de la venta",
                "PAGO_EXCEDE_TOTAL",
            )

    return _accion(
        "registrar_pago",
        True,
        contexto={
            "id_venta": venta.id_venta,
            "saldo_pendiente": round(saldo, 2),
        },
    )


def evaluar_registrar_pago_ot(
    db: Session,
    orden: OrdenTrabajo,
    usuario: Usuario,
    venta: Optional[Venta] = None,
    *,
    monto: Optional[Decimal | float] = None,
) -> AccionEvaluada:
    venta_resuelta = venta if venta is not None else _venta_activa_por_orden(db, orden.id)
    return evaluar_registrar_pago(db, venta_resuelta, usuario, monto=monto)


def evaluar_crear_venta_desde_ot(
    db: Session,
    orden: OrdenTrabajo,
    usuario: Usuario,
) -> AccionEvaluada:
    """Mismas reglas que ot_acciones_service (T5); fuente canónica post-P4.0."""
    rol = _rol_usuario(usuario)
    if rol not in ROLES_CAJA:
        return _accion(
            "crear_venta_desde_ot",
            False,
            f"Rol {rol} no puede crear ventas desde OT",
            "ROL_NO_PERMITIDO",
        )

    est = _estado_orden(orden)
    if est not in ("COMPLETADA", "ENTREGADA"):
        return _accion(
            "crear_venta_desde_ot",
            False,
            f"Solo se puede crear venta desde órdenes COMPLETADAS o ENTREGADAS (estado actual: {est})",
            "ESTADO_INVALIDO",
        )

    venta = _venta_activa_por_orden(db, orden.id)
    if venta:
        return _accion(
            "crear_venta_desde_ot",
            False,
            "Ya existe venta vinculada",
            "VENTA_EXISTENTE",
        )

    return _accion("crear_venta_desde_ot", True)
