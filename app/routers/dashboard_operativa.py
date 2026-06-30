"""
Lógica operativa del Dashboard V2 — candidatos, scoring, recomendación y salud.

Solo lectura. Sin servicios nuevos: funciones cohesivas consumidas por dashboard_agregado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config.dashboard_prioridades import (
    ACCIONES_FRECUENTES,
    FACTORES_ANTIGUEDAD_MIN,
    FACTORES_IMPACTO_MONTO,
    FACTORES_PROXIMIDAD_MIN,
    LABEL_FAMILIA,
    MAX_ITEMS_POR_GRUPO,
    ORDEN_FAMILIAS,
    PESO_BASE_FAMILIA,
    RECOMENDACION_ESTABLE,
    RUTA_FAMILIA,
    SEVERIDAD_ORDEN,
    UMBRALES_SEVERIDAD_ITEM,
    VER_TODAS_FAMILIA,
)
from app.models.caja_alerta import CajaAlerta
from app.models.caja_turno import CajaTurno
from app.models.cita import Cita, EstadoCita
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.services.operaciones_service import (
    SALDO_EPSILON,
    _ids_ordenes_ot_pendientes_cobro,
    _iter_ot_pendientes_cobro,
    _resumen_inventario_alertas,
    _venta_activa_por_orden,
    _venta_pertenece_v1,
    calcular_saldo_venta,
)
from app.utils.fechas import ahora_local, condiciones_rango_taller, hoy_taller, ingreso_ot_en_dia_taller


@dataclass
class CandidatoOperativo:
    grupo: str
    item_id: str
    titulo: str
    subtitulo: Optional[str]
    to: str
    referencia: Optional[dict]
    minutos_antiguedad: float = 0.0
    minutos_proximidad: Optional[float] = None
    impacto_monto: float = 0.0
    explicacion_extra: list[str] = field(default_factory=list)


def _factor_por_umbrales(valor: float, umbrales: tuple[tuple[float, float], ...]) -> float:
    for umbral, factor in umbrales:
        if valor <= umbral:
            return factor
    return umbrales[-1][1]


def calcular_decision_score(candidato: CandidatoOperativo) -> float:
    """decision_score = peso_base × antigüedad × proximidad × impacto."""
    peso = PESO_BASE_FAMILIA.get(candidato.grupo, 50.0)
    f_ant = _factor_por_umbrales(candidato.minutos_antiguedad, FACTORES_ANTIGUEDAD_MIN)
    if candidato.minutos_proximidad is not None:
        f_prox = _factor_por_umbrales(candidato.minutos_proximidad, FACTORES_PROXIMIDAD_MIN)
    else:
        f_prox = 1.0
    f_imp = 1.0
    for umbral, factor in FACTORES_IMPACTO_MONTO:
        if candidato.impacto_monto >= umbral:
            f_imp = factor
            break
    return round(peso * f_ant * f_prox * f_imp, 2)


def severidad_desde_score(score: float) -> str:
    for umbral, severidad in UMBRALES_SEVERIDAD_ITEM:
        if score >= umbral:
            return severidad
    return "baja"


def _minutos_desde_utc(dt: Optional[datetime]) -> float:
    if not dt:
        return 0.0
    ref = dt.replace(tzinfo=None) if dt.tzinfo else dt
    return max(0.0, (datetime.utcnow() - ref).total_seconds() / 60.0)


def _minutos_desde_local(dt: Optional[datetime]) -> float:
    if not dt:
        return 0.0
    ref = dt.replace(tzinfo=None) if dt.tzinfo else dt
    ahora = ahora_local()
    return max(0.0, (ahora - ref).total_seconds() / 60.0)


def _minutos_hasta_local(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    ref = dt.replace(tzinfo=None) if dt.tzinfo else dt
    ahora = ahora_local()
    delta = (ref - ahora).total_seconds() / 60.0
    return max(0.0, delta)


def _fmt_minutos_legible(minutos: float) -> str:
    if minutos < 60:
        return f"{int(minutos)} min"
    horas = minutos / 60.0
    if horas < 24:
        return f"{horas:.1f} h"
    return f"{horas / 24:.1f} días"


def _explicaciones_candidato(candidato: CandidatoOperativo, score: float) -> list[str]:
    partes: list[str] = []
    if candidato.minutos_antiguedad > 30:
        partes.append(f"Lleva {_fmt_minutos_legible(candidato.minutos_antiguedad)} sin atención")
    if candidato.impacto_monto > 0:
        partes.append(f"Monto involucrado: ${candidato.impacto_monto:,.2f}")
    if candidato.minutos_proximidad is not None and candidato.minutos_proximidad <= 240:
        partes.append(f"Evento en {_fmt_minutos_legible(candidato.minutos_proximidad)}")
    partes.extend(candidato.explicacion_extra)
    if not partes:
        partes.append(f"Prioridad operativa (score {score:.0f})")
    return partes[:3]


def _candidato_a_item(candidato: CandidatoOperativo) -> dict:
    score = calcular_decision_score(candidato)
    return {
        "id": candidato.item_id,
        "titulo": candidato.titulo,
        "subtitulo": candidato.subtitulo,
        "severidad": severidad_desde_score(score),
        "decision_score": score,
        "to": candidato.to,
        "referencia": candidato.referencia,
    }


def _extraer_candidatos_cobros(db: Session) -> list[CandidatoOperativo]:
    items: list[CandidatoOperativo] = []
    for orden, venta, saldo in _iter_ot_pendientes_cobro(db):
        ref_dt = orden.fecha_finalizacion or orden.fecha_ingreso
        monto = float(saldo or orden.total or 0)
        cliente = orden.cliente.nombre if orden.cliente else "Cliente"
        items.append(
            CandidatoOperativo(
                grupo="cobros",
                item_id=f"ot-{orden.id}",
                titulo=f"OT {orden.numero_orden} — cobro pendiente",
                subtitulo=f"{cliente} · ${monto:,.2f}",
                to=RUTA_FAMILIA["cobros"],
                referencia={"tipo": "orden_trabajo", "id": orden.id},
                minutos_antiguedad=_minutos_desde_utc(ref_dt),
                impacto_monto=monto,
            )
        )

    ids_o1 = _ids_ordenes_ot_pendientes_cobro(db)
    ventas = (
        db.query(Venta)
        .filter(Venta.estado != "CANCELADA")
        .order_by(Venta.fecha.desc())
        .limit(200)
        .all()
    )
    for venta in ventas:
        saldo = calcular_saldo_venta(db, venta)
        if saldo <= SALDO_EPSILON or not _venta_pertenece_v1(venta, ids_o1):
            continue
        items.append(
            CandidatoOperativo(
                grupo="cobros",
                item_id=f"venta-{venta.id_venta}",
                titulo=f"Venta #{venta.id_venta} — saldo pendiente",
                subtitulo=f"${saldo:,.2f}",
                to=RUTA_FAMILIA["cobros"],
                referencia={"tipo": "venta", "id": venta.id_venta},
                minutos_antiguedad=_minutos_desde_utc(venta.fecha),
                impacto_monto=float(saldo),
            )
        )
    return items


def _extraer_candidatos_entregas(db: Session) -> list[CandidatoOperativo]:
    items: list[CandidatoOperativo] = []
    ordenes = (
        db.query(OrdenTrabajo)
        .options(joinedload(OrdenTrabajo.cliente))
        .filter(OrdenTrabajo.estado == EstadoOrden.COMPLETADA)
        .order_by(OrdenTrabajo.fecha_finalizacion.desc())
        .limit(100)
        .all()
    )
    for orden in ordenes:
        venta = _venta_activa_por_orden(db, orden.id)
        if not venta:
            continue
        saldo = calcular_saldo_venta(db, venta)
        if saldo > SALDO_EPSILON:
            continue
        ref_dt = orden.fecha_finalizacion or orden.fecha_ingreso
        cliente = orden.cliente.nombre if orden.cliente else "Cliente"
        items.append(
            CandidatoOperativo(
                grupo="entregas",
                item_id=f"ot-{orden.id}",
                titulo=f"OT {orden.numero_orden} — lista para entrega",
                subtitulo=cliente,
                to=RUTA_FAMILIA["entregas"],
                referencia={"tipo": "orden_trabajo", "id": orden.id},
                minutos_antiguedad=_minutos_desde_utc(ref_dt),
            )
        )
    return items


def _extraer_candidatos_autorizaciones(db: Session) -> list[CandidatoOperativo]:
    items: list[CandidatoOperativo] = []
    ordenes = (
        db.query(OrdenTrabajo)
        .options(joinedload(OrdenTrabajo.cliente))
        .filter(OrdenTrabajo.estado == EstadoOrden.ESPERANDO_AUTORIZACION)
        .order_by(OrdenTrabajo.fecha_ingreso.asc())
        .limit(50)
        .all()
    )
    for orden in ordenes:
        cliente = orden.cliente.nombre if orden.cliente else "Cliente"
        items.append(
            CandidatoOperativo(
                grupo="autorizaciones",
                item_id=f"ot-{orden.id}",
                titulo=f"OT {orden.numero_orden} — esperando autorización",
                subtitulo=cliente,
                to=RUTA_FAMILIA["autorizaciones"],
                referencia={"tipo": "orden_trabajo", "id": orden.id},
                minutos_antiguedad=_minutos_desde_utc(orden.fecha_ingreso),
                impacto_monto=float(orden.total or 0),
            )
        )
    return items


def _extraer_candidatos_citas(db: Session) -> list[CandidatoOperativo]:
    items: list[CandidatoOperativo] = []
    ahora = ahora_local()

    citas_vencidas = (
        db.query(Cita)
        .options(joinedload(Cita.cliente))
        .filter(Cita.estado == EstadoCita.CONFIRMADA, Cita.fecha_hora <= ahora)
        .order_by(Cita.fecha_hora.asc())
        .limit(30)
        .all()
    )
    for cita in citas_vencidas:
        nombre = cita.cliente.nombre if cita.cliente else "Cliente"
        items.append(
            CandidatoOperativo(
                grupo="citas",
                item_id=f"cita-{cita.id_cita}",
                titulo=f"Cita vencida — {nombre}",
                subtitulo="Confirmar asistencia o convertir a OT",
                to=RUTA_FAMILIA["citas"],
                referencia={"tipo": "cita", "id": cita.id_cita},
                minutos_antiguedad=_minutos_desde_local(cita.fecha_hora),
                explicacion_extra=["Hora de cita ya pasó (hora local del taller)"],
            )
        )

    limite = ahora + timedelta(hours=24)
    citas_proximas = (
        db.query(Cita)
        .options(joinedload(Cita.cliente))
        .filter(
            Cita.estado == EstadoCita.CONFIRMADA,
            Cita.fecha_hora > ahora,
            Cita.fecha_hora <= limite,
        )
        .order_by(Cita.fecha_hora.asc())
        .limit(30)
        .all()
    )
    for cita in citas_proximas:
        nombre = cita.cliente.nombre if cita.cliente else "Cliente"
        prox = _minutos_hasta_local(cita.fecha_hora)
        items.append(
            CandidatoOperativo(
                grupo="citas",
                item_id=f"cita-{cita.id_cita}",
                titulo=f"Cita próxima — {nombre}",
                subtitulo="Preparar recepción",
                to=RUTA_FAMILIA["citas"],
                referencia={"tipo": "cita", "id": cita.id_cita},
                minutos_proximidad=prox,
                explicacion_extra=["Cita en las próximas 24 h (America/Matamoros)"],
            )
        )

    citas_convertibles = (
        db.query(Cita)
        .options(joinedload(Cita.cliente))
        .filter(
            Cita.estado.in_([EstadoCita.CONFIRMADA, EstadoCita.SI_ASISTIO]),
            Cita.id_orden.is_(None),
            Cita.fecha_hora >= ahora - timedelta(days=1),
        )
        .order_by(Cita.fecha_hora.asc())
        .limit(20)
        .all()
    )
    for cita in citas_convertibles:
        if any(i.item_id == f"cita-{cita.id_cita}" for i in items):
            continue
        nombre = cita.cliente.nombre if cita.cliente else "Cliente"
        items.append(
            CandidatoOperativo(
                grupo="citas",
                item_id=f"cita-{cita.id_cita}",
                titulo=f"Cita convertible — {nombre}",
                subtitulo="Convertir a orden de trabajo",
                to=RUTA_FAMILIA["citas"],
                referencia={"tipo": "cita", "id": cita.id_cita},
                minutos_antiguedad=_minutos_desde_local(cita.fecha_hora) if cita.fecha_hora <= ahora else 0.0,
                minutos_proximidad=_minutos_hasta_local(cita.fecha_hora),
            )
        )
    return items


def _extraer_candidatos_inventario(db: Session) -> list[CandidatoOperativo]:
    items: list[CandidatoOperativo] = []
    resumen = _resumen_inventario_alertas(db)
    if resumen.get("alertas_criticas", 0) > 0:
        items.append(
            CandidatoOperativo(
                grupo="inventario",
                item_id="inv-criticas",
                titulo=f"{resumen['alertas_criticas']} alertas críticas de stock",
                subtitulo="Revisar inventario",
                to=RUTA_FAMILIA["inventario"],
                referencia={"tipo": "inventario", "id": "alertas_criticas"},
                impacto_monto=0.0,
                explicacion_extra=["Stock crítico detectado"],
            )
        )
    sin_stock = (
        db.query(func.count(Repuesto.id_repuesto))
        .filter(Repuesto.activo, not Repuesto.eliminado, Repuesto.stock_actual == 0)
        .scalar()
        or 0
    )
    if sin_stock > 0:
        items.append(
            CandidatoOperativo(
                grupo="inventario",
                item_id="inv-sin-stock",
                titulo=f"{sin_stock} productos sin stock",
                subtitulo="Reabastecer o solicitar compra",
                to=RUTA_FAMILIA["inventario"],
                referencia={"tipo": "inventario", "id": "sin_stock"},
                explicacion_extra=[f"{sin_stock} repuestos activos en cero"],
            )
        )
    return items


def _extraer_candidatos_caja(db: Session, usuario: Usuario) -> list[CandidatoOperativo]:
    items: list[CandidatoOperativo] = []
    turno = (
        db.query(CajaTurno)
        .filter(CajaTurno.id_usuario == usuario.id_usuario, CajaTurno.estado == "ABIERTO")
        .first()
    )
    if turno and turno.fecha_apertura:
        minutos = _minutos_desde_utc(turno.fecha_apertura)
        if minutos >= 12 * 60:
            items.append(
                CandidatoOperativo(
                    grupo="caja",
                    item_id=f"turno-{turno.id_turno}",
                    titulo="Turno de caja abierto por mucho tiempo",
                    subtitulo=f"Lleva {_fmt_minutos_legible(minutos)} abierto",
                    to=RUTA_FAMILIA["caja"],
                    referencia={"tipo": "caja_turno", "id": turno.id_turno},
                    minutos_antiguedad=minutos,
                    explicacion_extra=["Considerar cierre de turno"],
                )
            )

    criticas = (
        db.query(func.count(CajaAlerta.id_alerta))
        .filter(not CajaAlerta.resuelta, CajaAlerta.nivel == "CRITICO")
        .scalar()
        or 0
    )
    if criticas > 0:
        items.append(
            CandidatoOperativo(
                grupo="caja",
                item_id="caja-alertas-criticas",
                titulo=f"{criticas} alertas críticas de caja",
                subtitulo="Revisar en Caja Operativa",
                to=RUTA_FAMILIA["caja"],
                referencia={"tipo": "caja_alerta", "id": "criticas"},
                explicacion_extra=["Alertas de caja sin resolver"],
            )
        )
    return items


def extraer_candidatos(db: Session, usuario: Usuario) -> list[CandidatoOperativo]:
    candidatos: list[CandidatoOperativo] = []
    candidatos.extend(_extraer_candidatos_cobros(db))
    candidatos.extend(_extraer_candidatos_entregas(db))
    candidatos.extend(_extraer_candidatos_autorizaciones(db))
    candidatos.extend(_extraer_candidatos_citas(db))
    candidatos.extend(_extraer_candidatos_inventario(db))
    candidatos.extend(_extraer_candidatos_caja(db, usuario))
    return candidatos


def _orden_familia(grupo: str) -> int:
    try:
        return ORDEN_FAMILIAS.index(grupo)
    except ValueError:
        return 999


def _peor_severidad(severidades: list[str]) -> str:
    for sev in SEVERIDAD_ORDEN:
        if sev in severidades:
            return sev
    return "baja"


def construir_prioridades_agrupadas(candidatos: list[CandidatoOperativo]) -> list[dict]:
    por_grupo: dict[str, list[CandidatoOperativo]] = {g: [] for g in ORDEN_FAMILIAS}
    for c in candidatos:
        if c.grupo in por_grupo:
            por_grupo[c.grupo].append(c)

    grupos_out: list[dict] = []
    for grupo in ORDEN_FAMILIAS:
        lista = por_grupo.get(grupo, [])
        if not lista:
            continue
        lista_ordenada = sorted(
            lista,
            key=lambda c: (-calcular_decision_score(c), _orden_familia(c.grupo)),
        )
        items = [_candidato_a_item(c) for c in lista_ordenada[:MAX_ITEMS_POR_GRUPO]]
        severidades = [i["severidad"] for i in items]
        bloque: dict[str, Any] = {
            "grupo": grupo,
            "label": LABEL_FAMILIA.get(grupo, grupo),
            "severidad_grupo": _peor_severidad(severidades),
            "total": len(lista_ordenada),
            "items": items,
        }
        if len(lista_ordenada) > MAX_ITEMS_POR_GRUPO:
            bloque["ver_todas"] = VER_TODAS_FAMILIA.get(grupo, {"to": "/", "label": "Ver todas"})
        grupos_out.append(bloque)

    grupos_out.sort(
        key=lambda g: (_orden_familia(g["grupo"]), -max((i["decision_score"] for i in g["items"]), default=0))
    )
    return grupos_out


def seleccionar_recomendacion_inteligente(candidatos: list[CandidatoOperativo]) -> dict:
    if not candidatos:
        return dict(RECOMENDACION_ESTABLE)

    mejor = max(
        candidatos,
        key=lambda c: (calcular_decision_score(c), -_orden_familia(c.grupo)),
    )
    score = calcular_decision_score(mejor)
    return {
        "titulo": mejor.titulo,
        "accion_label": "Ir ahora",
        "to": mejor.to,
        "severidad": severidad_desde_score(score),
        "grupo": mejor.grupo,
        "decision_score": score,
        "explicacion": _explicaciones_candidato(mejor, score),
        "referencia": mejor.referencia,
    }


def _estado_area_desde_severidad(severidad: str) -> str:
    if severidad == "critica":
        return "rojo"
    if severidad in ("alta", "media"):
        return "amarillo"
    return "verde"


def construir_salud_operativa(candidatos: list[CandidatoOperativo]) -> dict:
    areas_map = {
        "recepcion": ("autorizaciones", "citas"),
        "caja": ("cobros", "caja"),
        "taller": ("entregas",),
        "inventario": ("inventario",),
    }
    scores_por_grupo: dict[str, float] = {}
    sev_por_grupo: dict[str, str] = {}
    for c in candidatos:
        score = calcular_decision_score(c)
        sev = severidad_desde_score(score)
        if score > scores_por_grupo.get(c.grupo, 0):
            scores_por_grupo[c.grupo] = score
            sev_por_grupo[c.grupo] = sev

    areas: dict[str, dict] = {}
    peores: list[str] = []
    for area, grupos in areas_map.items():
        severidades = [sev_por_grupo[g] for g in grupos if g in sev_por_grupo]
        if not severidades:
            areas[area] = {"estado": "verde", "mensaje": "Sin pendientes relevantes"}
            peores.append("verde")
            continue
        peor = _peor_severidad(severidades)
        estado = _estado_area_desde_severidad(peor)
        areas[area] = {
            "estado": estado,
            "mensaje": f"Atención {peor} en {', '.join(grupos)}",
        }
        peores.append(estado)

    if "rojo" in peores:
        global_estado = "rojo"
        mensaje = "Hay áreas que requieren acción inmediata"
    elif "amarillo" in peores:
        global_estado = "amarillo"
        mensaje = "Operación estable con pendientes a atender"
    else:
        global_estado = "verde"
        mensaje = "Todas las áreas en verde"

    return {"global": global_estado, "mensaje": mensaje, "areas": areas}


def construir_resumen_ligero(db: Session, usuario: Usuario) -> dict:
    hoy = hoy_taller()
    hoy_str = hoy.isoformat()

    cobrado_hoy = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .join(Venta, Pago.id_venta == Venta.id_venta)
        .filter(Venta.estado != "CANCELADA")
    )
    for cond in condiciones_rango_taller(Pago.fecha, hoy_str, hoy_str):
        cobrado_hoy = cobrado_hoy.filter(cond)
    cobrado_val = float(cobrado_hoy.scalar() or 0)

    ventas_hoy = (
        db.query(func.coalesce(func.sum(Venta.total), 0))
        .filter(Venta.estado != "CANCELADA")
    )
    for cond in condiciones_rango_taller(Venta.fecha, hoy_str, hoy_str):
        ventas_hoy = ventas_hoy.filter(cond)
    ventas_val = float(ventas_hoy.scalar() or 0)

    ot_activas = (
        db.query(func.count(OrdenTrabajo.id))
        .filter(
            OrdenTrabajo.estado.in_(
                [
                    EstadoOrden.PENDIENTE,
                    EstadoOrden.EN_PROCESO,
                    EstadoOrden.ESPERANDO_AUTORIZACION,
                    EstadoOrden.ESPERANDO_REPUESTOS,
                ]
            )
        )
        .scalar()
        or 0
    )

    ahora = ahora_local()
    citas_24h = (
        db.query(func.count(Cita.id_cita))
        .filter(
            Cita.estado == EstadoCita.CONFIRMADA,
            Cita.fecha_hora >= ahora,
            Cita.fecha_hora <= ahora + timedelta(hours=24),
        )
        .scalar()
        or 0
    )

    por_cobrar = 0.0
    for _orden, _venta, saldo in _iter_ot_pendientes_cobro(db):
        por_cobrar += float(saldo or 0)
    ids_o1 = _ids_ordenes_ot_pendientes_cobro(db)
    ventas_pend = db.query(Venta).filter(Venta.estado != "CANCELADA").limit(300).all()
    for venta in ventas_pend:
        saldo = calcular_saldo_venta(db, venta)
        if saldo > SALDO_EPSILON and _venta_pertenece_v1(venta, ids_o1):
            por_cobrar += saldo

    turno = (
        db.query(CajaTurno)
        .filter(CajaTurno.id_usuario == usuario.id_usuario, CajaTurno.estado == "ABIERTO")
        .first()
    )
    caja_resumen = (
        {"turno_abierto": True, "id_turno": turno.id_turno}
        if turno
        else {"turno_abierto": False, "id_turno": None}
    )

    return {
        "caja": caja_resumen,
        "cobrado_hoy": cobrado_val,
        "ventas_hoy": ventas_val,
        "ot_activas": int(ot_activas),
        "citas_proximas_24h": int(citas_24h),
        "por_cobrar": round(por_cobrar, 2),
    }


def construir_bloque_operativa(db: Session, usuario: Usuario) -> dict:
    candidatos = extraer_candidatos(db, usuario)
    return {
        "recomendacion_inteligente": seleccionar_recomendacion_inteligente(candidatos),
        "salud_operativa": construir_salud_operativa(candidatos),
        "prioridades_agrupadas": construir_prioridades_agrupadas(candidatos),
        "resumen": construir_resumen_ligero(db, usuario),
        "acciones_frecuentes": list(ACCIONES_FRECUENTES),
    }
