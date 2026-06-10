"""
Evaluación centralizada de acciones sobre órdenes de trabajo.

Fuente única de verdad para:
- GET /api/operaciones/resumen (A0 acciones por ítem)
- GET /api/ordenes-trabajo/{id} (acciones[] opcional)
- POST mutaciones en acciones.py (asegurar_accion_ot_permitida)

DEPRECADO (compatibilidad temporal):
- ALLOW_TECNICO_SELF_ASSIGN: TECNICO puede iniciar OT sin tecnico_id previo.
  Plan futuro: False cuando Mi Taller + asignación obligatoria estén en prod.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.orden_trabajo import OrdenTrabajo
from app.models.pago import Pago
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.routers.ordenes_trabajo.helpers import MSG_ORDEN_SIN_ITEMS, orden_tiene_servicios_o_repuestos
from app.services import acciones_operativas_service

# Compatibilidad temporal — ver docstring del módulo.
ALLOW_TECNICO_SELF_ASSIGN = True

SALDO_EPSILON = 0.001

ROLES_INICIAR_FINALIZAR = frozenset({"ADMIN", "TECNICO"})
ROLES_CAJA = frozenset({"ADMIN", "CAJA"})
ROLES_COTIZACION_ENVIADA = frozenset({"ADMIN", "CAJA", "TECNICO"})

ESTADOS_INICIAR = frozenset({"PENDIENTE", "COTIZADA", "ESPERANDO_AUTORIZACION"})

ACCIONES_OPERATIVAS_DEFAULT = (
    "iniciar_ot",
    "finalizar_ot",
    "marcar_cotizacion_enviada",
    "autorizar_orden",
    "rechazar_orden",
    "entregar_vehiculo",
    "cancelar_orden",
    "reactivar_orden",
    "crear_venta_desde_ot",
    "pausar_refaccion",
)


@dataclass(frozen=True)
class AccionEvaluada:
    accion: str
    permitida: bool
    motivo_bloqueo: Optional[str] = None
    codigo_bloqueo: Optional[str] = None


def _rol_usuario(usuario: Usuario) -> str:
    return usuario.rol.value if hasattr(usuario.rol, "value") else str(usuario.rol)


def _estado_orden(orden: OrdenTrabajo) -> str:
    return orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)


def _accion(
    nombre: str,
    permitida: bool,
    motivo: Optional[str] = None,
    codigo: Optional[str] = None,
) -> AccionEvaluada:
    return AccionEvaluada(
        accion=nombre,
        permitida=permitida,
        motivo_bloqueo=motivo if not permitida else None,
        codigo_bloqueo=codigo if not permitida else None,
    )


def _venta_activa_por_orden(db: Session, orden_id: int) -> Optional[Venta]:
    return (
        db.query(Venta)
        .filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA")
        .order_by(Venta.id_venta.desc())
        .first()
    )


def _saldo_venta(db: Session, venta: Venta) -> float:
    total_pagado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .filter(Pago.id_venta == venta.id_venta)
        .scalar()
    )
    return max(0.0, float(venta.total) - float(total_pagado or 0))


def _tecnico_puede_operar(orden: OrdenTrabajo, usuario: Usuario) -> tuple[bool, Optional[str], Optional[str]]:
    """Valida asignación de técnico para acciones operativas del técnico."""
    rol = _rol_usuario(usuario)
    if rol != "TECNICO":
        return True, None, None
    if orden.tecnico_id is None:
        if ALLOW_TECNICO_SELF_ASSIGN:
            return True, None, None
        return False, "Debe asignar un técnico a la orden antes de iniciarla.", "SIN_TECNICO"
    if orden.tecnico_id != usuario.id_usuario:
        return False, "No tiene permiso para realizar esta acción", "TECNICO_NO_ASIGNADO"
    return True, None, None


def _evaluar_stock_inicio(db: Session, orden: OrdenTrabajo) -> tuple[bool, Optional[str], Optional[str]]:
    if getattr(orden, "cliente_proporciono_refacciones", False):
        return True, None, None
    for detalle in orden.detalles_repuesto or []:
        if not detalle.repuesto_id:
            continue
        repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == detalle.repuesto_id).first()
        if not repuesto:
            return (
                False,
                f"Repuesto con ID {detalle.repuesto_id} no encontrado",
                "REPUESTO_NO_ENCONTRADO",
            )
        if repuesto.stock_actual < detalle.cantidad:
            return (
                False,
                f"Stock insuficiente de {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Necesario: {detalle.cantidad}",
                "STOCK_INSUFICIENTE",
            )
    return True, None, None


def evaluar_iniciar_ot(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    rol = _rol_usuario(usuario)
    if rol not in ROLES_INICIAR_FINALIZAR:
        return _accion("iniciar_ot", False, f"Rol {rol} no puede iniciar órdenes de trabajo", "ROL_NO_PERMITIDO")

    est = _estado_orden(orden)
    if est not in ESTADOS_INICIAR:
        return _accion(
            "iniciar_ot",
            False,
            f"No se puede iniciar una orden en estado {est}",
            "ESTADO_INVALIDO",
        )

    if not orden_tiene_servicios_o_repuestos(orden):
        return _accion("iniciar_ot", False, MSG_ORDEN_SIN_ITEMS, "SIN_ITEMS")

    if orden.requiere_autorizacion and not orden.autorizado:
        return _accion(
            "iniciar_ot",
            False,
            "La orden requiere autorización del cliente antes de iniciar",
            "SIN_AUTORIZACION",
        )

    if rol == "TECNICO":
        ok_tec, motivo_tec, codigo_tec = _tecnico_puede_operar(orden, usuario)
        if not ok_tec:
            return _accion("iniciar_ot", False, motivo_tec, codigo_tec)
    elif not orden.tecnico_id:
        return _accion(
            "iniciar_ot",
            False,
            "Debe asignar un técnico a la orden antes de iniciarla. Edita la orden y asigna un técnico.",
            "SIN_TECNICO",
        )

    ok_stock, motivo_stock, codigo_stock = _evaluar_stock_inicio(db, orden)
    if not ok_stock:
        return _accion("iniciar_ot", False, motivo_stock, codigo_stock)

    return _accion("iniciar_ot", True)


def evaluar_finalizar_ot(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    del db  # reservado para reglas futuras
    rol = _rol_usuario(usuario)
    if rol not in ROLES_INICIAR_FINALIZAR:
        return _accion("finalizar_ot", False, f"Rol {rol} no puede finalizar órdenes de trabajo", "ROL_NO_PERMITIDO")

    if rol == "TECNICO" and orden.tecnico_id != usuario.id_usuario:
        return _accion("finalizar_ot", False, "No tiene permiso para finalizar esta orden", "TECNICO_NO_ASIGNADO")

    est = _estado_orden(orden)
    if est != "EN_PROCESO":
        return _accion(
            "finalizar_ot",
            False,
            f"Solo se pueden finalizar órdenes en proceso (estado actual: {est})",
            "ESTADO_INVALIDO",
        )

    if not orden_tiene_servicios_o_repuestos(orden):
        return _accion("finalizar_ot", False, MSG_ORDEN_SIN_ITEMS, "SIN_ITEMS")

    return _accion("finalizar_ot", True)


def evaluar_marcar_cotizacion_enviada(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    del db
    rol = _rol_usuario(usuario)
    if rol not in ROLES_COTIZACION_ENVIADA:
        return _accion("marcar_cotizacion_enviada", False, f"Rol {rol} no puede marcar cotización enviada", "ROL_NO_PERMITIDO")

    est = _estado_orden(orden)
    if est != "PENDIENTE":
        return _accion(
            "marcar_cotizacion_enviada",
            False,
            f"Solo se puede marcar cotización enviada en órdenes PENDIENTE (estado actual: {est})",
            "ESTADO_INVALIDO",
        )

    if not orden_tiene_servicios_o_repuestos(orden):
        return _accion("marcar_cotizacion_enviada", False, MSG_ORDEN_SIN_ITEMS, "SIN_ITEMS")

    return _accion("marcar_cotizacion_enviada", True)


def evaluar_autorizar_orden(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    del db
    rol = _rol_usuario(usuario)
    if rol not in ROLES_CAJA:
        return _accion("autorizar_orden", False, f"Rol {rol} no puede autorizar órdenes", "ROL_NO_PERMITIDO")
    if not orden.requiere_autorizacion:
        return _accion("autorizar_orden", False, "Esta orden no requiere autorización", "NO_REQUIERE_AUTORIZACION")
    return _accion("autorizar_orden", True)


def evaluar_rechazar_orden(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    base = evaluar_autorizar_orden(db, orden, usuario)
    return _accion("rechazar_orden", base.permitida, base.motivo_bloqueo, base.codigo_bloqueo)


def evaluar_entregar_vehiculo(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    rol = _rol_usuario(usuario)
    if rol not in ROLES_CAJA:
        return _accion("entregar_vehiculo", False, f"Rol {rol} no puede entregar vehículos", "ROL_NO_PERMITIDO")

    est = _estado_orden(orden)
    if est != "COMPLETADA":
        return _accion(
            "entregar_vehiculo",
            False,
            f"Solo se pueden entregar órdenes completadas (estado actual: {est})",
            "ESTADO_INVALIDO",
        )

    venta = _venta_activa_por_orden(db, orden.id)
    if not venta:
        return _accion(
            "entregar_vehiculo",
            False,
            "No puedes entregar: debes crear la venta y pagarla antes de entregar (Crea venta → registra pago en menú Ventas).",
            "SIN_VENTA",
        )

    saldo = _saldo_venta(db, venta)
    if saldo > SALDO_EPSILON:
        return _accion(
            "entregar_vehiculo",
            False,
            "No puedes entregar: la venta aún no ha sido pagada. Registra el pago en menú Ventas antes de entregar.",
            "VENTA_SIN_PAGAR",
        )

    return _accion("entregar_vehiculo", True)


def evaluar_cancelar_orden(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    del db
    rol = _rol_usuario(usuario)
    if rol not in ROLES_CAJA:
        return _accion("cancelar_orden", False, f"Rol {rol} no puede cancelar órdenes", "ROL_NO_PERMITIDO")

    est = _estado_orden(orden)
    if est == "ENTREGADA":
        return _accion("cancelar_orden", False, "No se puede cancelar una orden ya entregada", "ESTADO_INVALIDO")

    return _accion("cancelar_orden", True)


def evaluar_reactivar_orden(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    rol = _rol_usuario(usuario)
    if rol not in ROLES_CAJA:
        return _accion("reactivar_orden", False, f"Rol {rol} no puede reactivar órdenes", "ROL_NO_PERMITIDO")

    est = _estado_orden(orden)
    if est != "CANCELADA":
        return _accion(
            "reactivar_orden",
            False,
            f"Solo se pueden reactivar órdenes canceladas (estado actual: {est})",
            "ESTADO_INVALIDO",
        )

    venta = _venta_activa_por_orden(db, orden.id)
    if venta:
        return _accion(
            "reactivar_orden",
            False,
            "No se puede reactivar: hay una venta activa vinculada. Desvincula la venta primero.",
            "VENTA_VINCULADA",
        )

    return _accion("reactivar_orden", True)


def evaluar_crear_venta_desde_ot(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    resultado = acciones_operativas_service.evaluar_crear_venta_desde_ot(db, orden, usuario)
    return _accion(
        resultado.accion,
        resultado.permitida,
        resultado.motivo_bloqueo,
        resultado.codigo_bloqueo,
    )


def evaluar_pausar_refaccion(db: Session, orden: OrdenTrabajo, usuario: Usuario) -> AccionEvaluada:
    del db, orden, usuario
    return _accion("pausar_refaccion", False, "Acción no disponible todavía", "NO_IMPLEMENTADO")


_EVALUADORES = {
    "iniciar_ot": evaluar_iniciar_ot,
    "finalizar_ot": evaluar_finalizar_ot,
    "marcar_cotizacion_enviada": evaluar_marcar_cotizacion_enviada,
    "autorizar_orden": evaluar_autorizar_orden,
    "rechazar_orden": evaluar_rechazar_orden,
    "entregar_vehiculo": evaluar_entregar_vehiculo,
    "cancelar_orden": evaluar_cancelar_orden,
    "reactivar_orden": evaluar_reactivar_orden,
    "crear_venta_desde_ot": evaluar_crear_venta_desde_ot,
    "pausar_refaccion": evaluar_pausar_refaccion,
}


def evaluar_accion_ot(
    db: Session,
    orden: OrdenTrabajo,
    usuario: Usuario,
    accion: str,
) -> AccionEvaluada:
    evaluador = _EVALUADORES.get(accion)
    if not evaluador:
        return _accion(accion, False, f"Acción desconocida: {accion}", "ACCION_DESCONOCIDA")
    return evaluador(db, orden, usuario)


def evaluar_acciones_ot(
    db: Session,
    orden: OrdenTrabajo,
    usuario: Usuario,
    acciones: Optional[list[str]] = None,
) -> list[AccionEvaluada]:
    nombres = acciones if acciones is not None else list(ACCIONES_OPERATIVAS_DEFAULT)
    return [evaluar_accion_ot(db, orden, usuario, nombre) for nombre in nombres]


def acciones_a_dict(evaluadas: list[AccionEvaluada]) -> list[dict]:
    return [
        {
            "accion": a.accion,
            "permitida": a.permitida,
            "motivo_bloqueo": a.motivo_bloqueo,
            "codigo_bloqueo": a.codigo_bloqueo,
        }
        for a in evaluadas
    ]


def _http_status_para_codigo(codigo: Optional[str]) -> int:
    if codigo in ("TECNICO_NO_ASIGNADO", "ROL_NO_PERMITIDO"):
        return status.HTTP_403_FORBIDDEN
    if codigo == "REPUESTO_NO_ENCONTRADO":
        return status.HTTP_404_NOT_FOUND
    return status.HTTP_400_BAD_REQUEST


def asegurar_accion_ot_permitida(
    db: Session,
    orden: OrdenTrabajo,
    usuario: Usuario,
    accion: str,
) -> AccionEvaluada:
    """Lanza HTTPException con el mismo criterio que evaluar_accion_ot si no está permitida."""
    resultado = evaluar_accion_ot(db, orden, usuario, accion)
    if not resultado.permitida:
        raise HTTPException(
            status_code=_http_status_para_codigo(resultado.codigo_bloqueo),
            detail=resultado.motivo_bloqueo or "Acción no permitida",
        )
    return resultado
