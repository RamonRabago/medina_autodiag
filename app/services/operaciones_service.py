"""
Capa Operativa Central A0 — agregación de lectura para bandejas operativas.

No modifica datos. No ejecuta mutaciones.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.alerta_inventario import AlertaInventario, TipoAlertaInventario
from app.models.caja_turno import CajaTurno
from app.models.cita import Cita, EstadoCita
from app.models.cliente import Cliente
from app.models.cotizacion_refaccion_especial import (
    CotizacionRefaccionEspecial,
    EstadoCotizacionRefaccion,
)
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo, PrioridadOrden
from app.models.pago import Pago
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.services.cita_estado_service import calcular_estado_meta
from app.services.recepcion_ot_service import evaluar_cita_convertible
from app.services.ot_acciones_service import acciones_a_dict, evaluar_acciones_ot
from app.utils.fechas import ahora_local

SALDO_EPSILON = 0.001
VERSION_CONTRATO = "a0-v1"

ROLES_RECEPCION = frozenset({"ADMIN", "CAJA", "EMPLEADO"})
ROLES_CAJA = frozenset({"ADMIN", "CAJA"})
ROLES_INICIAR_OT = frozenset({"ADMIN", "TECNICO"})

ESTADOS_OT_PENDIENTES = frozenset({
    EstadoOrden.PENDIENTE,
    EstadoOrden.COTIZADA,
    EstadoOrden.ESPERANDO_AUTORIZACION,
    EstadoOrden.ESPERANDO_REPUESTOS,
})

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
    total_pagado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .filter(Pago.id_venta == venta.id_venta)
        .scalar()
    )
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
    """Expone permisos existentes del sistema; no inventa reglas nuevas."""
    puede_recepcion = rol in ROLES_RECEPCION
    puede_caja = rol in ROLES_CAJA
    puede_iniciar = rol in ROLES_INICIAR_OT

    return [
        _accion("convertir_cita_ot", puede_recepcion, None if puede_recepcion else f"Rol {rol} no puede convertir citas a OT"),
        _accion("recepcion_rapida", puede_recepcion, None if puede_recepcion else f"Rol {rol} no tiene acceso a recepción rápida"),
        _accion("iniciar_ot", puede_iniciar, None if puede_iniciar else f"Rol {rol} no puede iniciar órdenes de trabajo"),
        _accion("finalizar_ot", puede_iniciar, None if puede_iniciar else f"Rol {rol} no puede finalizar órdenes de trabajo"),
        _accion("registrar_pago", puede_caja, None if puede_caja else f"Rol {rol} no puede registrar pagos"),
        _accion("entregar_vehiculo", puede_caja, None if puede_caja else f"Rol {rol} no puede entregar vehículos"),
    ]


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


def _acciones_ot_pendientes_cobro(db: Session, orden: OrdenTrabajo, rol: str, usuario: Usuario, venta: Optional[Venta]) -> list[dict]:
    puede_caja = rol in ROLES_CAJA
    if venta:
        return [
            _accion("crear_venta_desde_ot", False, "Ya existe venta vinculada"),
            _accion(
                "registrar_pago",
                puede_caja,
                None if puede_caja else f"Rol {rol} no puede registrar pagos",
            ),
        ]

    crear_ev = evaluar_acciones_ot(db, orden, usuario, acciones=["crear_venta_desde_ot"])[0]
    return [
        {
            "accion": crear_ev.accion,
            "permitida": crear_ev.permitida,
            "motivo_bloqueo": crear_ev.motivo_bloqueo,
            "codigo_bloqueo": crear_ev.codigo_bloqueo,
        },
        _accion("registrar_pago", False, "Primero debe existir una venta vinculada"),
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
        "fecha_ingreso": orden.fecha_ingreso.isoformat() if orden.fecha_ingreso else None,
        "prioridad": _estado_str(orden.prioridad),
        "acciones": acciones,
    }
    if extras:
        item.update(extras)
    return item


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
        items.append({
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
        })
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
        items.append({
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
        })
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
        items.append(_serializar_orden_base(
            orden,
            acciones,
            {
                "estado_operativo": estado_operativo,
                "etiqueta_estado": ETIQUETAS_ESTADO_OT.get(estado_operativo, estado_db),
                "prioridad_sugerida": _prioridad_sugerida_ot(orden),
            },
        ))
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
        items.append(_serializar_orden_base(
            orden,
            acciones,
            {
                "estado_operativo": estado_db,
                "etiqueta_estado": ETIQUETAS_ESTADO_OT.get(estado_db, estado_db),
                "prioridad_sugerida": _prioridad_sugerida_ot(orden),
            },
        ))
    return total, items


def bandeja_ot_pendientes_cobro(db: Session, rol: str, usuario: Usuario, limit: int) -> tuple[int, list[dict]]:
    q = (
        _query_ot_base(db, None)
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .order_by(OrdenTrabajo.fecha_finalizacion.desc())
    )
    ordenes = q.all()
    pendientes = []
    for orden in ordenes:
        venta = _venta_activa_por_orden(db, orden.id)
        if venta is None:
            pendientes.append((orden, None, None))
            continue
        saldo = calcular_saldo_venta(db, venta)
        if saldo > SALDO_EPSILON:
            pendientes.append((orden, venta, saldo))

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


def bandeja_ventas_saldo_pendiente(db: Session, rol: str, limit: int) -> tuple[int, list[dict]]:
    ventas = (
        db.query(Venta)
        .filter(Venta.estado != "CANCELADA")
        .order_by(Venta.fecha.desc())
        .all()
    )
    pendientes = []
    for venta in ventas:
        saldo = calcular_saldo_venta(db, venta)
        if saldo > SALDO_EPSILON:
            pendientes.append((venta, saldo))

    total = len(pendientes)
    items = []
    for venta, saldo in pendientes[:limit]:
        cliente = db.query(Cliente).filter(Cliente.id_cliente == venta.id_cliente).first() if venta.id_cliente else None
        origen_tipo, origen_id = resolver_origen_venta(venta)
        items.append({
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
                _accion(
                    "registrar_pago",
                    rol in ROLES_CAJA,
                    None if rol in ROLES_CAJA else f"Rol {rol} no puede registrar pagos",
                ),
            ],
        })
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
        alertas.append({
            "codigo": "CITA_VENCIDA_SIN_ASISTENCIA",
            "severidad": "media",
            "mensaje": f"{n} cita(s) confirmada(s) ya pasaron su hora sin registrar asistencia",
            "cantidad": n,
        })

    inv = _resumen_inventario_alertas(db)
    if inv.get("alertas_criticas", 0) > 0:
        n = inv["alertas_criticas"]
        alertas.append({
            "codigo": "INVENTARIO_CRITICO",
            "severidad": "alta",
            "mensaje": f"{n} alerta(s) de inventario críticas",
            "cantidad": n,
        })

    if metricas.get("ot_pendientes_cobro", 0) > 0:
        n = metricas["ot_pendientes_cobro"]
        alertas.append({
            "codigo": "OT_PENDIENTE_COBRO",
            "severidad": "media",
            "mensaje": f"{n} orden(es) completada(s) pendientes de cobro",
            "cantidad": n,
        })

    return alertas


def construir_resumen_operativo(
    db: Session,
    usuario: Usuario,
    *,
    limit_items: int = 15,
    incluir_items: bool = True,
) -> dict[str, Any]:
    rol = _rol_usuario(usuario)
    ahora = ahora_local()

    tecnico_filtro = usuario.id_usuario if rol == "TECNICO" else None
    ver_citas = _puede_ver_citas(rol) or rol == "ADMIN"
    ver_financiero = _puede_ver_bandeja_financiera(rol)

    if ver_citas:
        total_asist, items_asist = bandeja_citas_pendientes_asistencia(
            db, rol, limit_items if incluir_items else 0
        )
        total_conv, items_conv = bandeja_citas_convertibles(db, rol, limit_items if incluir_items else 0)
    else:
        total_asist, items_asist = 0, []
        total_conv, items_conv = 0, []

    if rol == "TECNICO":
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(db, rol, usuario, limit_items if incluir_items else 0, tecnico_filtro)
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(db, rol, usuario, limit_items if incluir_items else 0, tecnico_filtro)
        total_ot_cobro, items_ot_cobro = 0, []
        total_ot_entrega, items_ot_entrega = 0, []
        total_ventas, items_ventas = 0, []
    elif ver_financiero:
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(db, rol, usuario, limit_items if incluir_items else 0, None)
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(db, rol, usuario, limit_items if incluir_items else 0, None)
        total_ot_cobro, items_ot_cobro = bandeja_ot_pendientes_cobro(db, rol, usuario, limit_items if incluir_items else 0)
        total_ot_entrega, items_ot_entrega = bandeja_ot_listas_entrega(db, rol, usuario, limit_items if incluir_items else 0)
        total_ventas, items_ventas = bandeja_ventas_saldo_pendiente(db, rol, limit_items if incluir_items else 0)
    elif rol == "EMPLEADO":
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(db, rol, usuario, limit_items if incluir_items else 0, None)
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(db, rol, usuario, limit_items if incluir_items else 0, None)
        total_ot_cobro, items_ot_cobro = 0, []
        total_ot_entrega, items_ot_entrega = 0, []
        total_ventas, items_ventas = 0, []
    else:
        total_ot_pend, items_ot_pend = bandeja_ot_pendientes(db, rol, usuario, limit_items if incluir_items else 0, None)
        total_ot_proc, items_ot_proc = bandeja_ot_en_proceso(db, rol, usuario, limit_items if incluir_items else 0, None)
        total_ot_cobro, items_ot_cobro = bandeja_ot_pendientes_cobro(db, rol, usuario, limit_items if incluir_items else 0)
        total_ot_entrega, items_ot_entrega = bandeja_ot_listas_entrega(db, rol, usuario, limit_items if incluir_items else 0)
        total_ventas, items_ventas = bandeja_ventas_saldo_pendiente(db, rol, limit_items if incluir_items else 0)

    ref_compra, ref_recibidas = contadores_refacciones(db)

    metricas = {
        "citas_pendientes_asistencia": total_asist,
        "citas_convertibles": total_conv,
        "ot_pendientes": total_ot_pend,
        "ot_en_proceso": total_ot_proc,
        "ot_pendientes_cobro": total_ot_cobro,
        "ot_listas_entrega": total_ot_entrega,
        "ventas_saldo_pendiente": total_ventas,
        "refacciones_en_compra": ref_compra,
        "refacciones_recibidas_pendiente_entrega": ref_recibidas,
    }

    caja = _info_caja(db, usuario) if ver_financiero else {
        "turno_abierto": False,
        "id_turno": None,
        "alerta_turno_largo": False,
    }

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
