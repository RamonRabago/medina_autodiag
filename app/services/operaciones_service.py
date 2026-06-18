"""
Capa Operativa Central A0 — agregación de lectura para bandejas operativas.

No modifica datos. No ejecuta mutaciones.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.alerta_inventario import AlertaInventario, TipoAlertaInventario
from app.models.caja_turno import CajaTurno
from app.models.cita import Cita, EstadoCita
from app.models.cliente import Cliente
from app.models.cotizacion_refaccion_especial import (
    CotizacionRefaccionEspecial,
    EstadoCotizacionRefaccion,
)
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.services import acciones_operativas_service
from app.services.cita_estado_service import calcular_estado_meta
from app.services.ot_acciones_service import acciones_a_dict, evaluar_acciones_ot
from app.services.recepcion_ot_service import evaluar_cita_convertible
from app.utils.fechas import ahora_local, isoformat_fecha_ingreso_ot

SALDO_EPSILON = 0.001
VERSION_CONTRATO = "a0-v2"
VERSION_CONTRATO_SLICE = "a0-v2.1"

MAX_BANDEJAS_SLICE = 8

GRUPOS_SLICE_VALIDOS = frozenset({"caja", "recepcion", "mi_taller", "refacciones"})

BANDEJAS_WHITELIST = frozenset(
    {
        "citas_pendientes_asistencia",
        "citas_convertibles",
        "ot_pendientes",
        "ot_en_proceso",
        "ot_completadas",
        "ot_pendientes_cobro",
        "ot_listas_entrega",
        "ventas_saldo_pendiente",
    }
)

GRUPO_BANDEJAS_MAP: dict[str, tuple[str, ...]] = {
    "caja": ("ot_pendientes_cobro", "ot_listas_entrega", "ventas_saldo_pendiente"),
    "recepcion": ("citas_pendientes_asistencia", "citas_convertibles"),
    "mi_taller": ("ot_pendientes", "ot_en_proceso", "ot_completadas"),
    "refacciones": (),
}

BANDEJA_A_METRICA: dict[str, str] = {
    "citas_pendientes_asistencia": "citas_pendientes_asistencia",
    "citas_convertibles": "citas_convertibles",
    "ot_pendientes": "ot_pendientes",
    "ot_en_proceso": "ot_en_proceso",
    "ot_completadas": "ot_completadas",
    "ot_pendientes_cobro": "ot_pendientes_cobro",
    "ot_listas_entrega": "ot_listas_entrega",
    "ventas_saldo_pendiente": "ventas_saldo_pendiente",
}


class OperacionesSliceParamError(ValueError):
    """Params slice A0 v2.1 inválidos — mapear a HTTP 422 en router."""


def validar_params_slice(
    grupo: Optional[str],
    bandejas: Optional[str],
    incluir_items: bool,
) -> Optional[list[str]]:
    """
    Valida params slice y devuelve lista ordenada de bandejas a hidratar.
    None si no hay modo slice (legacy/capa0).
    """
    grupo_norm = grupo.strip().lower() if grupo and grupo.strip() else None
    bandejas_provided = bandejas is not None

    if bandejas_provided and not bandejas.strip() and not grupo_norm:
        raise OperacionesSliceParamError("bandejas vacío")

    if not bandejas_provided and not grupo_norm:
        return None

    if not incluir_items:
        raise OperacionesSliceParamError(
            "incluir_items=false incompatible con params slice grupo/bandejas"
        )

    if bandejas_provided and bandejas.strip():
        tokens = [t.strip() for t in bandejas.split(",") if t.strip()]
        if not tokens:
            raise OperacionesSliceParamError("bandejas vacío")
        if len(tokens) > MAX_BANDEJAS_SLICE:
            raise OperacionesSliceParamError(
                f"máximo {MAX_BANDEJAS_SLICE} bandejas por request"
            )
        invalid = [t for t in tokens if t not in BANDEJAS_WHITELIST]
        if invalid:
            raise OperacionesSliceParamError(f"bandejas inválidas: {', '.join(invalid)}")
        seen: set[str] = set()
        ordered: list[str] = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                ordered.append(token)
        return ordered

    assert grupo_norm is not None
    if grupo_norm not in GRUPOS_SLICE_VALIDOS:
        raise OperacionesSliceParamError(f"grupo inválido: {grupo_norm}")
    return list(GRUPO_BANDEJAS_MAP[grupo_norm])

ROLES_RECEPCION = frozenset({"ADMIN", "CAJA", "EMPLEADO"})
ROLES_CAJA = frozenset({"ADMIN", "CAJA"})
ROLES_INICIAR_OT = frozenset({"ADMIN", "TECNICO"})

ESTADOS_OT_PENDIENTES = frozenset(
    {
        EstadoOrden.PENDIENTE,
        EstadoOrden.COTIZADA,
        EstadoOrden.ESPERANDO_AUTORIZACION,
        EstadoOrden.ESPERANDO_REPUESTOS,
    }
)

ETIQUETAS_ESTADO_OT: dict[str, str] = {
    "PENDIENTE": "Pendiente recepción",
    "COTIZADA": "Cotizada",
    "ESPERANDO_AUTORIZACION": "Esperando autorización",
    "ESPERANDO_REFACCION": "Esperando refacción",
    "EN_PROCESO": "En proceso",
    "COMPLETADA": "Completada",
    "ENTREGADA": "Entregada",
    "CANCELADA": "Cancelada",
}


def _rol_usuario(usuario: Usuario) -> str:
    return usuario.rol.value if hasattr(usuario.rol, "value") else str(usuario.rol)


def _estado_str(valor) -> str:
    return valor.value if hasattr(valor, "value") else str(valor)


def _vehiculo_resumen(vehiculo) -> Optional[str]:
    if not vehiculo:
        return None
    return f"{vehiculo.marca} {vehiculo.modelo} {vehiculo.anio}".strip()


def calcular_saldo_venta(db: Session, venta: Venta) -> float:
    """Mismo cálculo que ventas/crud: total - sum(pagos), mínimo 0."""
    total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == venta.id_venta).scalar()
    return max(0.0, float(venta.total) - float(total_pagado or 0))


def resolver_origen_venta(venta: Venta) -> tuple[str, Optional[int]]:
    """
    Trazabilidad de origen para P4 Caja Operativa.
    OT si hay id_orden; MOSTRADOR si venta sin OT; heurística comentarios para refacción.
    """
    if venta.id_orden:
        return "OT", int(venta.id_orden)
    com = (venta.comentarios or "").lower()
    if "refacc" in com or ("cotiz" in com and "ref" in com):
        return "REFACCION_ESPECIAL", None
    if not venta.id_orden:
        return "MOSTRADOR", int(venta.id_venta)
    return "OTRO", int(venta.id_venta)


def _estado_operativo_ot(estado_db: str) -> str:
    if estado_db == "ESPERANDO_REPUESTOS":
        return "ESPERANDO_REFACCION"
    return estado_db


def _prioridad_sugerida_ot(orden: OrdenTrabajo) -> str:
    prioridad = _estado_str(orden.prioridad)
    if prioridad in ("URGENTE", "ALTA"):
        return "ALTA"
    if orden.fecha_promesa and orden.fecha_promesa.replace(tzinfo=None) < datetime.utcnow():
        return "ALTA"
    if prioridad == "BAJA":
        return "BAJA"
    return "NORMAL"


def _accion(accion: str, permitida: bool, motivo: Optional[str] = None) -> dict:
    return {
        "accion": accion,
        "permitida": permitida,
        "motivo_bloqueo": motivo if not permitida else None,
    }


def acciones_globales_por_rol(rol: str) -> list[dict]:
    """
    Capacidades de sesión/navegación por rol + mutaciones financiero-operativas item_only (Opción A).
    Las acciones financieras nunca son permitida=true en global; evaluación real en acciones[] del ítem.
    """
    puede_recepcion = rol in ROLES_RECEPCION
    puede_iniciar = rol in ROLES_INICIAR_OT

    sesion_navegacion = [
        _accion(
            "convertir_cita_ot",
            puede_recepcion,
            None if puede_recepcion else f"Rol {rol} no puede convertir citas a OT",
        ),
        _accion(
            "recepcion_rapida",
            puede_recepcion,
            None if puede_recepcion else f"Rol {rol} no tiene acceso a recepción rápida",
        ),
        _accion(
            "iniciar_ot", puede_iniciar, None if puede_iniciar else f"Rol {rol} no puede iniciar órdenes de trabajo"
        ),
        _accion(
            "finalizar_ot", puede_iniciar, None if puede_iniciar else f"Rol {rol} no puede finalizar órdenes de trabajo"
        ),
    ]
    financieras_item_only = [
        acciones_operativas_service.accion_a_dict(ev)
        for ev in acciones_operativas_service.acciones_globales_financieras_item_only()
    ]
    return sesion_navegacion + financieras_item_only


def _puede_ver_bandeja_financiera(rol: str) -> bool:
    return rol in ROLES_CAJA or rol == "ADMIN"


def _puede_ver_citas(rol: str) -> bool:
    return rol in ROLES_RECEPCION or rol == "ADMIN"


def _resumen_inventario_alertas(db: Session) -> dict[str, int]:
    """Patrón estable de notificaciones/dashboard — solo lectura."""
    alertas = (
        db.query(AlertaInventario.tipo_alerta, func.count(AlertaInventario.id_alerta).label("cantidad"))
        .join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto)
        .filter(AlertaInventario.activa == True, Repuesto.eliminado == False)  # noqa: E712
        .group_by(AlertaInventario.tipo_alerta)
        .all()
    )
    resumen = {
        "total_alertas": 0,
        "alertas_criticas": 0,
    }
    for alerta in alertas:
        tipo = _estado_str(alerta.tipo_alerta)
        resumen["total_alertas"] += alerta.cantidad
        if tipo == TipoAlertaInventario.STOCK_CRITICO.value:
            resumen["alertas_criticas"] = alerta.cantidad
    return resumen


def _info_caja(db: Session, usuario: Usuario) -> dict:
    turno = (
        db.query(CajaTurno)
        .filter(
            CajaTurno.id_usuario == usuario.id_usuario,
            CajaTurno.estado == "ABIERTO",
        )
        .first()
    )
    if not turno:
        return {"turno_abierto": False, "id_turno": None, "alerta_turno_largo": False}

    alerta_largo = False
    if turno.fecha_apertura:
        duracion = datetime.utcnow() - turno.fecha_apertura
        alerta_largo = duracion >= timedelta(hours=12)

    return {
        "turno_abierto": True,
        "id_turno": turno.id_turno,
        "alerta_turno_largo": alerta_largo,
    }


def _venta_activa_por_orden(db: Session, orden_id: int) -> Optional[Venta]:
    return (
        db.query(Venta)
        .filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA")
        .order_by(Venta.id_venta.desc())
        .first()
    )


def _acciones_cita_item(cita: Cita, rol: str, eval_conv: dict) -> list[dict]:
    puede_recepcion = rol in ROLES_RECEPCION
    meta = calcular_estado_meta(cita, rol)
    puede_marcar = bool(meta.get("transiciones_permitidas"))
    conv = eval_conv.get("convertible", False) and puede_recepcion

    acciones = [
        _accion(
            "marcar_asistencia_cita",
            puede_marcar,
            None if puede_marcar else "No hay transiciones de estado permitidas para tu rol",
        ),
        _accion(
            "convertir_cita_ot",
            conv,
            None if conv else eval_conv.get("motivo") or "No se puede convertir esta cita",
        ),
    ]
    return acciones


def _acciones_ot_item(
    db: Session,
    orden: OrdenTrabajo,
    rol: str,
    usuario: Usuario,
    contexto: str,
) -> list[dict]:
    acciones_solicitadas: list[str] = []
    if contexto == "pendientes":
        acciones_solicitadas = ["iniciar_ot"]
    elif contexto == "en_proceso":
        acciones_solicitadas = ["finalizar_ot"]
    elif contexto == "listas_entrega":
        acciones_solicitadas = ["entregar_vehiculo"]

    if not acciones_solicitadas:
        return []

    evaluadas = evaluar_acciones_ot(db, orden, usuario, acciones=acciones_solicitadas)
    return acciones_a_dict(evaluadas)


def _acciones_ot_pendientes_cobro(
    db: Session, orden: OrdenTrabajo, rol: str, usuario: Usuario, venta: Optional[Venta]
) -> list[dict]:
    del rol
    # Coherencia O1: si el clasificador ya resolvió venta activa, bloquear sin re-query.
    if venta is not None:
        crear_ev = acciones_operativas_service.AccionEvaluada(
            accion="crear_venta_desde_ot",
            permitida=False,
            motivo_bloqueo="Ya existe venta vinculada",
            codigo_bloqueo="VENTA_EXISTENTE",
        )
    else:
        crear_ev = acciones_operativas_service.evaluar_crear_venta_desde_ot(db, orden, usuario)
    pago_ev = acciones_operativas_service.evaluar_registrar_pago_ot(db, orden, usuario, venta=venta)
    return [
        acciones_operativas_service.accion_a_dict(crear_ev),
        acciones_operativas_service.accion_a_dict(pago_ev),
    ]


def _serializar_orden_base(orden: OrdenTrabajo, acciones: list[dict], extras: Optional[dict] = None) -> dict:
    estado_db = _estado_str(orden.estado)
    item = {
        "tipo_entidad": "orden_trabajo",
        "id": orden.id,
        "numero_orden": orden.numero_orden,
        "estado": estado_db,
        "cliente_nombre": orden.cliente.nombre if orden.cliente else None,
        "vehiculo_resumen": _vehiculo_resumen(orden.vehiculo),
        "tecnico_nombre": orden.tecnico.nombre if getattr(orden, "tecnico", None) else None,
        "fecha_ingreso": isoformat_fecha_ingreso_ot(orden.fecha_ingreso),
        "prioridad": _estado_str(orden.prioridad),
        "acciones": acciones,
    }
    if extras:
        item.update(extras)
    return item


# --- P5.3 Fase 1 Commit B: contadores SQL simples (sin evaluadores; no cableados aún) ---


def _contar_citas_pendientes_asistencia(db: Session) -> int:
    """COUNT citas CONFIRMADA con hora vencida — paridad con bandeja_citas_pendientes_asistencia."""
    ahora = ahora_local()
    return int(
        db.query(func.count(Cita.id_cita))
        .filter(
            Cita.estado == EstadoCita.CONFIRMADA,
            Cita.fecha_hora <= ahora,
        )
        .scalar()
        or 0
    )


def _contar_citas_convertibles(db: Session) -> int:
    """COUNT citas convertibles sin OT vinculada — paridad con bandeja_citas_convertibles."""
    return int(
        db.query(func.count(Cita.id_cita))
        .filter(
            Cita.estado.in_([EstadoCita.CONFIRMADA, EstadoCita.SI_ASISTIO]),
            Cita.id_orden.is_(None),
        )
        .scalar()
        or 0
    )


def _contar_ot_pendientes(db: Session, tecnico_id: Optional[int] = None) -> int:
    """COUNT OT en estados pendientes — paridad con bandeja_ot_pendientes (solo total)."""
    q = db.query(func.count(OrdenTrabajo.id)).filter(OrdenTrabajo.estado.in_(list(ESTADOS_OT_PENDIENTES)))
    if tecnico_id is not None:
        q = q.filter(OrdenTrabajo.tecnico_id == tecnico_id)
    return int(q.scalar() or 0)


def _contar_ot_en_proceso(db: Session, tecnico_id: Optional[int] = None) -> int:
    """COUNT OT EN_PROCESO — paridad con bandeja_ot_en_proceso (solo total)."""
    q = db.query(func.count(OrdenTrabajo.id)).filter(OrdenTrabajo.estado == EstadoOrden.EN_PROCESO)
    if tecnico_id is not None:
        q = q.filter(OrdenTrabajo.tecnico_id == tecnico_id)
    return int(q.scalar() or 0)


def _contar_ot_completadas(db: Session, tecnico_id: Optional[int] = None) -> int:
    """COUNT OT COMPLETADA — paridad con bandeja_ot_completadas (solo total)."""
    q = db.query(func.count(OrdenTrabajo.id)).filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
    if tecnico_id is not None:
        q = q.filter(OrdenTrabajo.tecnico_id == tecnico_id)
    return int(q.scalar() or 0)


# --- P5.3 Fase 1 Commit C: contadores SQL financieros O1/O2/V1 (no cableados aún) ---


def _subquery_venta_activa_por_orden_agg(db: Session):
    """
    Agregado id_orden → venta activa (max id_venta no cancelada).
    Equivalente a _venta_activa_por_orden con ORDER BY id_venta DESC LIMIT 1.
    """
    return (
        db.query(
            Venta.id_orden.label("id_orden"),
            func.max(Venta.id_venta).label("id_venta_activa"),
        )
        .filter(Venta.estado != "CANCELADA", Venta.id_orden.isnot(None))
        .group_by(Venta.id_orden)
        .subquery("a0_venta_activa_por_orden")
    )


def _subquery_saldos_venta(db: Session):
    """id_venta → saldo (total - pagos, mínimo 0) — paridad con calcular_saldo_venta."""
    pagos_agg = (
        db.query(
            Pago.id_venta.label("id_venta"),
            func.coalesce(func.sum(Pago.monto), 0).label("total_pagado"),
        )
        .group_by(Pago.id_venta)
        .subquery("a0_pagos_por_venta")
    )
    return (
        db.query(
            Venta.id_venta.label("id_venta"),
            func.greatest(
                0,
                Venta.total - func.coalesce(pagos_agg.c.total_pagado, 0),
            ).label("saldo"),
        )
        .outerjoin(pagos_agg, Venta.id_venta == pagos_agg.c.id_venta)
        .subquery("a0_saldos_venta")
    )


def _query_ids_ordenes_o1(db: Session):
    """IDs de OT en clasificador O1 — paridad con _ids_ordenes_ot_pendientes_cobro."""
    va = _subquery_venta_activa_por_orden_agg(db)
    saldos = _subquery_saldos_venta(db)
    return (
        db.query(OrdenTrabajo.id)
        .outerjoin(va, OrdenTrabajo.id == va.c.id_orden)
        .outerjoin(saldos, va.c.id_venta_activa == saldos.c.id_venta)
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .filter(
            or_(
                va.c.id_venta_activa.is_(None),
                saldos.c.saldo > SALDO_EPSILON,
            )
        )
    )


def _contar_ot_pendientes_cobro(db: Session) -> int:
    """COUNT O1 — OT COMPLETADA sin venta activa o con saldo > ε."""
    va = _subquery_venta_activa_por_orden_agg(db)
    saldos = _subquery_saldos_venta(db)
    return int(
        db.query(func.count(OrdenTrabajo.id))
        .outerjoin(va, OrdenTrabajo.id == va.c.id_orden)
        .outerjoin(saldos, va.c.id_venta_activa == saldos.c.id_venta)
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .filter(
            or_(
                va.c.id_venta_activa.is_(None),
                saldos.c.saldo > SALDO_EPSILON,
            )
        )
        .scalar()
        or 0
    )


def _contar_ot_listas_entrega(db: Session) -> int:
    """COUNT O2 — OT COMPLETADA con venta activa y saldo <= ε."""
    va = _subquery_venta_activa_por_orden_agg(db)
    saldos = _subquery_saldos_venta(db)
    return int(
        db.query(func.count(OrdenTrabajo.id))
        .join(va, OrdenTrabajo.id == va.c.id_orden)
        .join(saldos, va.c.id_venta_activa == saldos.c.id_venta)
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .filter(saldos.c.saldo <= SALDO_EPSILON)
        .scalar()
        or 0
    )


def _contar_ventas_saldo_pendiente(db: Session) -> int:
    """COUNT V1 — ventas con saldo > ε excluyendo OT ya en O1."""
    saldos = _subquery_saldos_venta(db)
    ids_o1 = _query_ids_ordenes_o1(db)
    return int(
        db.query(func.count(Venta.id_venta))
        .join(saldos, Venta.id_venta == saldos.c.id_venta)
        .filter(Venta.estado != "CANCELADA")
        .filter(saldos.c.saldo > SALDO_EPSILON)
        .filter(
            or_(
                Venta.id_orden.is_(None),
                ~Venta.id_orden.in_(ids_o1),
            )
        )
        .scalar()
        or 0
    )


def bandeja_citas_pendientes_asistencia(db: Session, rol: str, limit: int) -> tuple[int, list[dict]]:
    ahora = ahora_local()
    q = (
        db.query(Cita)
        .options(joinedload(Cita.cliente), joinedload(Cita.vehiculo))
        .filter(
            Cita.estado == EstadoCita.CONFIRMADA,
            Cita.fecha_hora <= ahora,
        )
        .order_by(Cita.fecha_hora.asc())
    )
    total = q.count()
    citas = q.limit(limit).all()
    items = []
    for c in citas:
        eval_conv = evaluar_cita_convertible(c)
        meta = calcular_estado_meta(c, rol)
        items.append(
            {
                "tipo_entidad": "cita",
                "id": c.id_cita,
                "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else None,
                "estado": _estado_str(c.estado),
                "cliente_nombre": c.cliente.nombre if c.cliente else None,
                "vehiculo_resumen": _vehiculo_resumen(c.vehiculo),
                "estado_meta": meta,
                "evaluacion_conversion": {
                    "convertible": eval_conv.get("convertible"),
                    "motivo": eval_conv.get("motivo"),
                },
                "acciones": _acciones_cita_item(c, rol, eval_conv),
            }
        )
    return total, items


def bandeja_citas_convertibles(db: Session, rol: str, limit: int) -> tuple[int, list[dict]]:
    q = (
        db.query(Cita)
        .options(joinedload(Cita.cliente), joinedload(Cita.vehiculo))
        .filter(
            Cita.estado.in_([EstadoCita.CONFIRMADA, EstadoCita.SI_ASISTIO]),
            Cita.id_orden.is_(None),
        )
        .order_by(Cita.fecha_hora.asc())
    )
    total = q.count()
    citas = q.limit(limit).all()
    items = []
    for c in citas:
        eval_conv = evaluar_cita_convertible(c)
        meta = calcular_estado_meta(c, rol)
        items.append(
            {
                "tipo_entidad": "cita",
                "id": c.id_cita,
                "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else None,
                "estado": _estado_str(c.estado),
                "cliente_nombre": c.cliente.nombre if c.cliente else None,
                "vehiculo_resumen": _vehiculo_resumen(c.vehiculo),
                "estado_meta": meta,
                "evaluacion_conversion": {
                    "convertible": eval_conv.get("convertible"),
                    "motivo": eval_conv.get("motivo"),
                },
                "acciones": _acciones_cita_item(c, rol, eval_conv),
            }
        )
    return total, items


def _query_ot_base(db: Session, tecnico_id: Optional[int] = None):
    q = db.query(OrdenTrabajo).options(
        joinedload(OrdenTrabajo.cliente),
        joinedload(OrdenTrabajo.vehiculo),
        joinedload(OrdenTrabajo.tecnico),
        joinedload(OrdenTrabajo.detalles_servicio),
        joinedload(OrdenTrabajo.detalles_repuesto),
    )
    if tecnico_id is not None:
        q = q.filter(OrdenTrabajo.tecnico_id == tecnico_id)
    return q


def bandeja_ot_pendientes(
    db: Session,
    rol: str,
    usuario: Usuario,
    limit: int,
    tecnico_id: Optional[int] = None,
) -> tuple[int, list[dict]]:
    q = _query_ot_base(db, tecnico_id).filter(OrdenTrabajo.estado.in_(list(ESTADOS_OT_PENDIENTES)))
    q = q.order_by(OrdenTrabajo.fecha_ingreso.asc())
    total = q.count()
    ordenes = q.limit(limit).all()
    items = []
    for orden in ordenes:
        estado_db = _estado_str(orden.estado)
        estado_operativo = _estado_operativo_ot(estado_db)
        acciones = _acciones_ot_item(db, orden, rol, usuario, "pendientes")
        items.append(
            _serializar_orden_base(
                orden,
                acciones,
                {
                    "estado_operativo": estado_operativo,
                    "etiqueta_estado": ETIQUETAS_ESTADO_OT.get(estado_operativo, estado_db),
                    "prioridad_sugerida": _prioridad_sugerida_ot(orden),
                },
            )
        )
    return total, items


def bandeja_ot_en_proceso(
    db: Session,
    rol: str,
    usuario: Usuario,
    limit: int,
    tecnico_id: Optional[int] = None,
) -> tuple[int, list[dict]]:
    q = _query_ot_base(db, tecnico_id).filter(OrdenTrabajo.estado == EstadoOrden.EN_PROCESO)
    q = q.order_by(OrdenTrabajo.fecha_ingreso.asc())
    total = q.count()
    ordenes = q.limit(limit).all()
    items = []
    for orden in ordenes:
        estado_db = _estado_str(orden.estado)
        acciones = _acciones_ot_item(db, orden, rol, usuario, "en_proceso")
        items.append(
            _serializar_orden_base(
                orden,
                acciones,
                {
                    "estado_operativo": estado_db,
                    "etiqueta_estado": ETIQUETAS_ESTADO_OT.get(estado_db, estado_db),
                    "prioridad_sugerida": _prioridad_sugerida_ot(orden),
                },
            )
        )
    return total, items


def bandeja_ot_completadas(
    db: Session,
    rol: str,
    usuario: Usuario,
    limit: int,
    tecnico_id: Optional[int] = None,
) -> tuple[int, list[dict]]:
    """OT COMPLETADAS recientes — solo lectura (sin acciones operativas)."""
    del rol, usuario
    q = _query_ot_base(db, tecnico_id).filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
    q = q.order_by(OrdenTrabajo.fecha_finalizacion.desc(), OrdenTrabajo.id.desc())
    total = q.count()
    ordenes = q.limit(limit).all() if limit else []
    items = []
    for orden in ordenes:
        estado_db = _estado_str(orden.estado)
        items.append(
            _serializar_orden_base(
                orden,
                [],
                {
                    "estado_operativo": estado_db,
                    "etiqueta_estado": ETIQUETAS_ESTADO_OT.get(estado_db, estado_db),
                    "prioridad_sugerida": _prioridad_sugerida_ot(orden),
                    "fecha_finalizacion": orden.fecha_finalizacion.isoformat() if orden.fecha_finalizacion else None,
                },
            )
        )
    return total, items


def _iter_ot_pendientes_cobro(db: Session):
    """
    Clasificador O1 (ADR §3.2): OT COMPLETADA sin venta activa o con saldo > ε.
    Fuente única para bandeja ot_pendientes_cobro y deduplicación V1.
    """
    q = (
        _query_ot_base(db, None)
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .order_by(OrdenTrabajo.fecha_finalizacion.desc())
    )
    for orden in q.all():
        venta = _venta_activa_por_orden(db, orden.id)
        if venta is None:
            yield orden, None, None
            continue
        saldo = calcular_saldo_venta(db, venta)
        if saldo > SALDO_EPSILON:
            yield orden, venta, saldo


def _ids_ordenes_ot_pendientes_cobro(db: Session) -> frozenset[int]:
    """IDs de OT presentes en O1 — usados para excluir duplicados en ventas_saldo_pendiente (V1)."""
    return frozenset(orden.id for orden, _, _ in _iter_ot_pendientes_cobro(db))


def _venta_pertenece_v1(venta: Venta, ids_o1: frozenset[int]) -> bool:
    """
    V1: venta activa con saldo > ε.
    Excluye ventas vinculadas a OT ya representadas en ot_pendientes_cobro (O1).
    Ventas mostrador (sin id_orden) siempre candidatas.
    """
    if venta.id_orden is None:
        return True
    return int(venta.id_orden) not in ids_o1


def bandeja_ot_pendientes_cobro(db: Session, rol: str, usuario: Usuario, limit: int) -> tuple[int, list[dict]]:
    pendientes = list(_iter_ot_pendientes_cobro(db))
    total = len(pendientes)
    items = []
    for orden, venta, saldo in pendientes[:limit]:
        acciones = _acciones_ot_pendientes_cobro(db, orden, rol, usuario, venta)
        extras = {
            "total_orden": float(orden.total or 0),
            "id_venta": venta.id_venta if venta else None,
            "saldo_pendiente": saldo,
            "estado_operativo": "PENDIENTE_COBRO",
            "etiqueta_estado": "Completada — pendiente de cobro",
            "prioridad_sugerida": _prioridad_sugerida_ot(orden),
        }
        items.append(_serializar_orden_base(orden, acciones, extras))
    return total, items


def bandeja_ot_listas_entrega(db: Session, rol: str, usuario: Usuario, limit: int) -> tuple[int, list[dict]]:
    q = (
        _query_ot_base(db, None)
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .order_by(OrdenTrabajo.fecha_finalizacion.desc())
    )
    ordenes = q.all()
    listas = []
    for orden in ordenes:
        venta = _venta_activa_por_orden(db, orden.id)
        if not venta:
            continue
        saldo = calcular_saldo_venta(db, venta)
        if saldo <= SALDO_EPSILON:
            listas.append((orden, venta, saldo))

    total = len(listas)
    items = []
    for orden, venta, saldo in listas[:limit]:
        acciones = _acciones_ot_item(db, orden, rol, usuario, "listas_entrega")
        extras = {
            "total_orden": float(orden.total or 0),
            "id_venta": venta.id_venta,
            "saldo_pendiente": saldo,
            "estado_operativo": "LISTA_ENTREGA",
            "etiqueta_estado": "Lista para entrega",
            "prioridad_sugerida": _prioridad_sugerida_ot(orden),
        }
        items.append(_serializar_orden_base(orden, acciones, extras))
    return total, items


def bandeja_ventas_saldo_pendiente(db: Session, rol: str, usuario: Usuario, limit: int) -> tuple[int, list[dict]]:
    ids_o1 = _ids_ordenes_ot_pendientes_cobro(db)
    ventas = db.query(Venta).filter(Venta.estado != "CANCELADA").order_by(Venta.fecha.desc()).all()
    pendientes = []
    for venta in ventas:
        saldo = calcular_saldo_venta(db, venta)
        if saldo > SALDO_EPSILON and _venta_pertenece_v1(venta, ids_o1):
            pendientes.append((venta, saldo))

    total = len(pendientes)
    items = []
    for venta, saldo in pendientes[:limit]:
        cliente = db.query(Cliente).filter(Cliente.id_cliente == venta.id_cliente).first() if venta.id_cliente else None
        origen_tipo, origen_id = resolver_origen_venta(venta)
        items.append(
            {
                "tipo_entidad": "venta",
                "id": venta.id_venta,
                "id_orden": venta.id_orden,
                "cliente_nombre": cliente.nombre if cliente else None,
                "total": float(venta.total),
                "saldo_pendiente": saldo,
                "estado": venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado),
                "origen_tipo": origen_tipo,
                "origen_id": origen_id,
                "acciones": [
                    acciones_operativas_service.accion_a_dict(
                        acciones_operativas_service.evaluar_registrar_pago(db, venta, usuario)
                    ),
                ],
            }
        )
    return total, items


def contadores_refacciones(db: Session) -> tuple[int, int]:
    en_compra = (
        db.query(func.count(CotizacionRefaccionEspecial.id))
        .filter(CotizacionRefaccionEspecial.estado == EstadoCotizacionRefaccion.EN_COMPRA)
        .scalar()
        or 0
    )
    recibidas = (
        db.query(func.count(CotizacionRefaccionEspecial.id))
        .filter(CotizacionRefaccionEspecial.estado == EstadoCotizacionRefaccion.RECIBIDA)
        .scalar()
        or 0
    )
    return int(en_compra), int(recibidas)


def alertas_operativas(db: Session, metricas: dict) -> list[dict]:
    alertas = []
    if metricas.get("citas_pendientes_asistencia", 0) > 0:
        n = metricas["citas_pendientes_asistencia"]
        alertas.append(
            {
                "codigo": "CITA_VENCIDA_SIN_ASISTENCIA",
                "severidad": "media",
                "mensaje": f"{n} cita(s) confirmada(s) ya pasaron su hora sin registrar asistencia",
                "cantidad": n,
            }
        )

    inv = _resumen_inventario_alertas(db)
    if inv.get("alertas_criticas", 0) > 0:
        n = inv["alertas_criticas"]
        alertas.append(
            {
                "codigo": "INVENTARIO_CRITICO",
                "severidad": "alta",
                "mensaje": f"{n} alerta(s) de inventario críticas",
                "cantidad": n,
            }
        )

    if metricas.get("ot_pendientes_cobro", 0) > 0:
        n = metricas["ot_pendientes_cobro"]
        alertas.append(
            {
                "codigo": "OT_PENDIENTE_COBRO",
                "severidad": "media",
                "mensaje": f"{n} orden(es) completada(s) pendientes de cobro",
                "cantidad": n,
            }
        )

    return alertas


def _construir_resumen_metricas_rapidas(
    db: Session,
    usuario: Usuario,
    *,
    limit_items: int,
) -> dict[str, Any]:
    """
    P5.3 Fase 1 Commit D — fast path genuino para incluir_items=false.
    Métricas vía contadores SQL; bandejas sin ítems ni evaluadores por fila.
    """
    rol = _rol_usuario(usuario)
    ahora = ahora_local()
    tecnico_filtro = usuario.id_usuario if rol == "TECNICO" else None
    ver_citas = _puede_ver_citas(rol) or rol == "ADMIN"
    ver_financiero = _puede_ver_bandeja_financiera(rol)

    if ver_citas:
        total_asist = _contar_citas_pendientes_asistencia(db)
        total_conv = _contar_citas_convertibles(db)
    else:
        total_asist, total_conv = 0, 0

    if rol == "TECNICO":
        total_ot_pend = _contar_ot_pendientes(db, tecnico_filtro)
        total_ot_proc = _contar_ot_en_proceso(db, tecnico_filtro)
        total_ot_compl = _contar_ot_completadas(db, tecnico_filtro)
        total_ot_cobro, total_ot_entrega, total_ventas = 0, 0, 0
    elif ver_financiero:
        total_ot_pend = _contar_ot_pendientes(db, None)
        total_ot_proc = _contar_ot_en_proceso(db, None)
        total_ot_cobro = _contar_ot_pendientes_cobro(db)
        total_ot_entrega = _contar_ot_listas_entrega(db)
        total_ventas = _contar_ventas_saldo_pendiente(db)
        total_ot_compl = _contar_ot_completadas(db, None) if rol == "ADMIN" else 0
    elif rol == "EMPLEADO":
        total_ot_pend = _contar_ot_pendientes(db, None)
        total_ot_proc = _contar_ot_en_proceso(db, None)
        total_ot_compl, total_ot_cobro, total_ot_entrega, total_ventas = 0, 0, 0, 0
    else:
        total_ot_pend = _contar_ot_pendientes(db, None)
        total_ot_proc = _contar_ot_en_proceso(db, None)
        total_ot_cobro = _contar_ot_pendientes_cobro(db)
        total_ot_entrega = _contar_ot_listas_entrega(db)
        total_ventas = _contar_ventas_saldo_pendiente(db)
        total_ot_compl = 0

    ref_compra, ref_recibidas = contadores_refacciones(db)

    metricas = {
        "citas_pendientes_asistencia": total_asist,
        "citas_convertibles": total_conv,
        "ot_pendientes": total_ot_pend,
        "ot_en_proceso": total_ot_proc,
        "ot_completadas": total_ot_compl,
        "ot_pendientes_cobro": total_ot_cobro,
        "ot_listas_entrega": total_ot_entrega,
        "ventas_saldo_pendiente": total_ventas,
        "refacciones_en_compra": ref_compra,
        "refacciones_recibidas_pendiente_entrega": ref_recibidas,
    }

    caja = (
        _info_caja(db, usuario)
        if ver_financiero
        else {
            "turno_abierto": False,
            "id_turno": None,
            "alerta_turno_largo": False,
        }
    )

    bandejas = {
        "citas_pendientes_asistencia": {"total": total_asist, "items": []},
        "citas_convertibles": {"total": total_conv, "items": []},
        "ot_pendientes": {"total": total_ot_pend, "items": []},
        "ot_en_proceso": {"total": total_ot_proc, "items": []},
        "ot_completadas": {"total": total_ot_compl, "items": []},
        "ot_pendientes_cobro": {"total": total_ot_cobro, "items": []},
        "ot_listas_entrega": {"total": total_ot_entrega, "items": []},
        "ventas_saldo_pendiente": {"total": total_ventas, "items": []},
    }

    return {
        "generado_en": ahora.isoformat(),
        "usuario": {
            "id_usuario": usuario.id_usuario,
            "rol": rol,
            "nombre": usuario.nombre,
        },
        "bloqueo_financiero": {
            "bloqueo_financiero": False,
            "motivo_bloqueo": None,
        },
        "acciones_globales": acciones_globales_por_rol(rol),
        "metricas": metricas,
        "bandejas": bandejas,
        "alertas_operativas": alertas_operativas(db, metricas),
        "caja": caja,
        "meta": {
            "limit_items": limit_items,
            "incluir_items": False,
            "version_contrato": VERSION_CONTRATO,
        },
    }


def _construir_resumen_completo(
    db: Session,
    usuario: Usuario,
    *,
    limit_items: int,
    incluir_items: bool,
) -> dict[str, Any]:
    """Camino legacy con bandejas y evaluadores — incluir_items=true."""
    rol = _rol_usuario(usuario)
    ahora = ahora_local()

    tecnico_filtro = usuario.id_usuario if rol == "TECNICO" else None
    ver_citas = _puede_ver_citas(rol) or rol == "ADMIN"
    ver_financiero = _puede_ver_bandeja_financiera(rol)

    if ver_citas:
        total_asist, items_asist = bandeja_citas_pendientes_asistencia(db, rol, limit_items if incluir_items else 0)
        total_conv, items_conv = bandeja_citas_convertibles(db, rol, limit_items if incluir_items else 0)
    else:
        total_asist, items_asist = 0, []
        total_conv, items_conv = 0, []

    if rol == "TECNICO":
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(
            db, rol, usuario, limit_items if incluir_items else 0, tecnico_filtro
        )
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(
            db, rol, usuario, limit_items if incluir_items else 0, tecnico_filtro
        )
        total_ot_compl, items_ot_compl = bandeja_ot_completadas(
            db, rol, usuario, limit_items if incluir_items else 0, tecnico_filtro
        )
        total_ot_cobro, items_ot_cobro = 0, []
        total_ot_entrega, items_ot_entrega = 0, []
        total_ventas, items_ventas = 0, []
    elif ver_financiero:
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(
            db, rol, usuario, limit_items if incluir_items else 0, None
        )
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(
            db, rol, usuario, limit_items if incluir_items else 0, None
        )
        total_ot_cobro, items_ot_cobro = bandeja_ot_pendientes_cobro(
            db, rol, usuario, limit_items if incluir_items else 0
        )
        total_ot_entrega, items_ot_entrega = bandeja_ot_listas_entrega(
            db, rol, usuario, limit_items if incluir_items else 0
        )
        total_ventas, items_ventas = bandeja_ventas_saldo_pendiente(
            db, rol, usuario, limit_items if incluir_items else 0
        )
        if rol == "ADMIN":
            total_ot_compl, items_ot_compl = bandeja_ot_completadas(
                db, rol, usuario, limit_items if incluir_items else 0, None
            )
        else:
            total_ot_compl, items_ot_compl = 0, []
    elif rol == "EMPLEADO":
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(
            db, rol, usuario, limit_items if incluir_items else 0, None
        )
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(
            db, rol, usuario, limit_items if incluir_items else 0, None
        )
        total_ot_compl, items_ot_compl = 0, []
        total_ot_cobro, items_ot_cobro = 0, []
        total_ot_entrega, items_ot_entrega = 0, []
        total_ventas, items_ventas = 0, []
    else:
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(
            db, rol, usuario, limit_items if incluir_items else 0, None
        )
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(
            db, rol, usuario, limit_items if incluir_items else 0, None
        )
        total_ot_cobro, items_ot_cobro = bandeja_ot_pendientes_cobro(
            db, rol, usuario, limit_items if incluir_items else 0
        )
        total_ot_entrega, items_ot_entrega = bandeja_ot_listas_entrega(
            db, rol, usuario, limit_items if incluir_items else 0
        )
        total_ventas, items_ventas = bandeja_ventas_saldo_pendiente(
            db, rol, usuario, limit_items if incluir_items else 0
        )
        total_ot_compl, items_ot_compl = 0, []

    ref_compra, ref_recibidas = contadores_refacciones(db)

    metricas = {
        "citas_pendientes_asistencia": total_asist,
        "citas_convertibles": total_conv,
        "ot_pendientes": total_ot_pend,
        "ot_en_proceso": total_ot_proc,
        "ot_completadas": total_ot_compl,
        "ot_pendientes_cobro": total_ot_cobro,
        "ot_listas_entrega": total_ot_entrega,
        "ventas_saldo_pendiente": total_ventas,
        "refacciones_en_compra": ref_compra,
        "refacciones_recibidas_pendiente_entrega": ref_recibidas,
    }

    caja = (
        _info_caja(db, usuario)
        if ver_financiero
        else {
            "turno_abierto": False,
            "id_turno": None,
            "alerta_turno_largo": False,
        }
    )

    bandejas = {
        "citas_pendientes_asistencia": {
            "total": total_asist,
            "items": items_asist if incluir_items else [],
        },
        "citas_convertibles": {
            "total": total_conv,
            "items": items_conv if incluir_items else [],
        },
        "ot_pendientes": {
            "total": total_ot_pend,
            "items": items_ot_pend if incluir_items else [],
        },
        "ot_en_proceso": {
            "total": total_ot_proc,
            "items": items_ot_proc if incluir_items else [],
        },
        "ot_completadas": {
            "total": total_ot_compl,
            "items": items_ot_compl if incluir_items else [],
        },
        "ot_pendientes_cobro": {
            "total": total_ot_cobro,
            "items": items_ot_cobro if incluir_items else [],
        },
        "ot_listas_entrega": {
            "total": total_ot_entrega,
            "items": items_ot_entrega if incluir_items else [],
        },
        "ventas_saldo_pendiente": {
            "total": total_ventas,
            "items": items_ventas if incluir_items else [],
        },
    }

    return {
        "generado_en": ahora.isoformat(),
        "usuario": {
            "id_usuario": usuario.id_usuario,
            "rol": rol,
            "nombre": usuario.nombre,
        },
        "bloqueo_financiero": {
            "bloqueo_financiero": False,
            "motivo_bloqueo": None,
        },
        "acciones_globales": acciones_globales_por_rol(rol),
        "metricas": metricas,
        "bandejas": bandejas,
        "alertas_operativas": alertas_operativas(db, metricas),
        "caja": caja,
        "meta": {
            "limit_items": limit_items,
            "incluir_items": incluir_items,
            "version_contrato": VERSION_CONTRATO,
        },
    }


def _puede_hidratar_bandeja(rol: str, bandeja_key: str) -> bool:
    """Mismos permisos que _construir_resumen_completo para incluir_items."""
    ver_citas = _puede_ver_citas(rol) or rol == "ADMIN"
    ver_financiero = _puede_ver_bandeja_financiera(rol)

    if bandeja_key in ("citas_pendientes_asistencia", "citas_convertibles"):
        return ver_citas

    if rol == "TECNICO":
        return bandeja_key in ("ot_pendientes", "ot_en_proceso", "ot_completadas")

    if ver_financiero:
        if bandeja_key == "ot_completadas":
            return rol == "ADMIN"
        return bandeja_key in (
            "ot_pendientes",
            "ot_en_proceso",
            "ot_pendientes_cobro",
            "ot_listas_entrega",
            "ventas_saldo_pendiente",
        )

    if rol == "EMPLEADO":
        return bandeja_key in ("ot_pendientes", "ot_en_proceso")

    if bandeja_key == "ot_completadas":
        return False
    return bandeja_key in (
        "ot_pendientes",
        "ot_en_proceso",
        "ot_pendientes_cobro",
        "ot_listas_entrega",
        "ventas_saldo_pendiente",
    )


def _hidratar_bandeja(
    db: Session,
    usuario: Usuario,
    bandeja_key: str,
    limit_items: int,
) -> tuple[int, list[dict]]:
    """Invoca evaluadores bandeja_* existentes — sin duplicar lógica."""
    rol = _rol_usuario(usuario)
    tecnico_filtro = usuario.id_usuario if rol == "TECNICO" else None

    if bandeja_key == "citas_pendientes_asistencia":
        return bandeja_citas_pendientes_asistencia(db, rol, limit_items)
    if bandeja_key == "citas_convertibles":
        return bandeja_citas_convertibles(db, rol, limit_items)
    if bandeja_key == "ot_pendientes":
        return bandeja_ot_pendientes(
            db, rol, usuario, limit_items, tecnico_filtro if rol == "TECNICO" else None
        )
    if bandeja_key == "ot_en_proceso":
        return bandeja_ot_en_proceso(
            db, rol, usuario, limit_items, tecnico_filtro if rol == "TECNICO" else None
        )
    if bandeja_key == "ot_completadas":
        return bandeja_ot_completadas(
            db, rol, usuario, limit_items, tecnico_filtro if rol == "TECNICO" else None
        )
    if bandeja_key == "ot_pendientes_cobro":
        return bandeja_ot_pendientes_cobro(db, rol, usuario, limit_items)
    if bandeja_key == "ot_listas_entrega":
        return bandeja_ot_listas_entrega(db, rol, usuario, limit_items)
    if bandeja_key == "ventas_saldo_pendiente":
        return bandeja_ventas_saldo_pendiente(db, rol, usuario, limit_items)
    raise ValueError(f"bandeja no soportada: {bandeja_key}")


def _construir_resumen_slice(
    db: Session,
    usuario: Usuario,
    *,
    limit_items: int,
    bandejas_solicitadas: list[str],
    grupo: Optional[str] = None,
) -> dict[str, Any]:
    """
    UX-1B.0 — capa métricas (contadores SQL) + hidratación selectiva de bandejas.
    """
    base = _construir_resumen_metricas_rapidas(db, usuario, limit_items=limit_items)
    hidratadas: list[str] = []

    for bandeja_key in bandejas_solicitadas:
        if not _puede_hidratar_bandeja(_rol_usuario(usuario), bandeja_key):
            continue
        total, items = _hidratar_bandeja(db, usuario, bandeja_key, limit_items)
        base["bandejas"][bandeja_key] = {"total": total, "items": items}
        metric_key = BANDEJA_A_METRICA[bandeja_key]
        base["metricas"][metric_key] = total
        hidratadas.append(bandeja_key)

    base["alertas_operativas"] = alertas_operativas(db, base["metricas"])

    meta = base["meta"]
    meta["version_contrato"] = VERSION_CONTRATO_SLICE
    meta["incluir_items"] = True
    meta["parcial"] = True
    meta["bandejas_hidratadas"] = hidratadas
    if grupo:
        meta["grupo"] = grupo
        meta["bandejas_solicitadas"] = list(GRUPO_BANDEJAS_MAP[grupo])
    else:
        meta["bandejas_solicitadas"] = list(bandejas_solicitadas)

    return base


def construir_resumen_operativo(
    db: Session,
    usuario: Usuario,
    *,
    limit_items: int = 15,
    incluir_items: bool = True,
    grupo: Optional[str] = None,
    bandejas: Optional[str] = None,
) -> dict[str, Any]:
    """
    Resumen operativo A0 v2 / v2.1.
    incluir_items=false → fast path P5.3 (contadores SQL).
    grupo / bandejas → slice v2.1 (UX-1B.0).
    incluir_items=true sin slice → bandejas completas con evaluadores (legacy).
    """
    bandejas_hidratar = validar_params_slice(grupo, bandejas, incluir_items)
    if bandejas_hidratar is not None:
        grupo_norm = grupo.strip().lower() if grupo and grupo.strip() and not (bandejas or "").strip() else None
        return _construir_resumen_slice(
            db,
            usuario,
            limit_items=limit_items,
            bandejas_solicitadas=bandejas_hidratar,
            grupo=grupo_norm,
        )
    if not incluir_items:
        return _construir_resumen_metricas_rapidas(db, usuario, limit_items=limit_items)
    return _construir_resumen_completo(
        db,
        usuario,
        limit_items=limit_items,
        incluir_items=True,
    )
