"""
Router agregado para Dashboard V2: un solo endpoint con secciones lazy.

GET /api/dashboard — default secciones=operativa (rápido).
Finanzas e inventario solo si se solicitan explícitamente.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.alerta_inventario import AlertaInventario
from app.models.caja_alerta import CajaAlerta
from app.models.cancelacion_producto import CancelacionProducto
from app.models.cliente import Cliente
from app.models.cuenta_pagar_manual import CuentaPagarManual
from app.models.gasto_operativo import GastoOperativo
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.orden_compra import EstadoOrdenCompra, OrdenCompra
from app.models.orden_trabajo import OrdenTrabajo
from app.models.pago import Pago
from app.models.pago_orden_compra import PagoOrdenCompra
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.routers.dashboard_operativa import construir_bloque_operativa
from app.services.devoluciones_service import query_devoluciones
from app.services.gastos_service import query_gastos
from app.services.inventario_service import InventarioService
from app.utils.decimal_utils import money_round, to_decimal
from app.utils.dependencies import get_current_user
from app.utils.fechas import (
    condiciones_rango_taller,
    hoy_taller,
    isoformat_utc,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

SECCIONES_VALIDAS = frozenset({"operativa", "finanzas", "inventario"})


def parse_secciones(secciones: Optional[str]) -> list[str]:
    """Parsea CSV de secciones. Default operativa. Desconocido → ValueError."""
    if secciones is None or not str(secciones).strip():
        return ["operativa"]
    tokens = [t.strip().lower() for t in str(secciones).split(",") if t.strip()]
    invalid = [t for t in tokens if t not in SECCIONES_VALIDAS]
    if invalid:
        raise ValueError(f"secciones inválidas: {', '.join(invalid)}")
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def _get_rango_periodo(periodo: str) -> tuple[Optional[str], Optional[str]]:
    """Retorna (fecha_desde, fecha_hasta) para el periodo indicado."""
    hoy = hoy_taller()
    año = hoy.year
    mes = hoy.month
    if periodo == "mes":
        desde = f"{año}-{mes:02d}-01"
        hasta = hoy.isoformat()
        return desde, hasta
    if periodo == "mes_pasado":
        from datetime import timedelta

        d = date(año, mes - 1, 1) if mes > 1 else date(año - 1, 12, 1)
        ultimo = (date(año, mes, 1) if mes < 12 else date(año + 1, 1, 1)) - timedelta(days=1)
        return d.isoformat(), ultimo.isoformat()
    if periodo == "ano":
        return f"{año}-01-01", hoy.isoformat()
    return None, None


def _build_inventario(db: Session) -> dict:
    valor_inv = InventarioService.calcular_valor_inventario(db)
    total_alertas = (
        db.query(func.count(AlertaInventario.id_alerta))
        .join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto)
        .filter(AlertaInventario.activa, not Repuesto.eliminado)
        .scalar()
        or 0
    )
    sin_stock = (
        db.query(func.count(Repuesto.id_repuesto))
        .filter(Repuesto.activo, not Repuesto.eliminado, Repuesto.stock_actual == 0)
        .scalar()
        or 0
    )
    stock_bajo = (
        db.query(func.count(Repuesto.id_repuesto))
        .filter(
            Repuesto.activo,
            not Repuesto.eliminado,
            Repuesto.stock_actual <= Repuesto.stock_minimo,
            Repuesto.stock_actual > 0,
        )
        .scalar()
        or 0
    )
    productos_activos = (
        db.query(func.count(Repuesto.id_repuesto)).filter(Repuesto.activo, not Repuesto.eliminado).scalar() or 0
    )
    base_oc = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_([EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.RECIBIDA_PARCIAL])
    )
    ordenes_sin_recibir = base_oc.count()
    hoy_dt_dt = datetime.combine(date.today(), datetime.min.time())
    ordenes_vencidas = base_oc.filter(
        OrdenCompra.fecha_estimada_entrega.isnot(None),
        OrdenCompra.fecha_estimada_entrega < hoy_dt_dt,
    ).count()
    return {
        "valor_inventario": valor_inv,
        "productos_activos": productos_activos,
        "stock_bajo": stock_bajo,
        "sin_stock": sin_stock,
        "total_alertas": total_alertas,
        "ordenes_compra_alertas": {
            "ordenes_sin_recibir": ordenes_sin_recibir,
            "ordenes_vencidas": ordenes_vencidas,
        },
    }


def _build_finanzas(db: Session, periodo: str, current_user: Usuario, es_admin: bool) -> dict:
    fecha_desde, fecha_hasta = _get_rango_periodo(periodo) if periodo != "acumulado" else (None, None)

    q_facturado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .join(Venta, Pago.id_venta == Venta.id_venta)
        .filter(Venta.estado != "CANCELADA")
    )
    for cond in condiciones_rango_taller(Pago.fecha, fecha_desde, fecha_hasta):
        q_facturado = q_facturado.filter(cond)
    total_facturado = float(q_facturado.scalar() or 0)

    q_ventas = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(Venta.estado != "CANCELADA")
    for cond in condiciones_rango_taller(Venta.fecha, fecha_desde, fecha_hasta):
        q_ventas = q_ventas.filter(cond)
    total_ventas_periodo = float(q_ventas.scalar() or 0)

    q_g = query_gastos(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    total_gastos = float(q_g.with_entities(func.coalesce(func.sum(GastoOperativo.monto), 0)).scalar() or 0)

    # Utilidad N+1 — solo en bloque finanzas
    from app.models.orden_trabajo import OrdenTrabajo as OT

    query_ventas = db.query(Venta).filter(Venta.estado != "CANCELADA")
    for cond in condiciones_rango_taller(Venta.fecha, fecha_desde, fecha_hasta):
        query_ventas = query_ventas.filter(cond)
    ventas = query_ventas.all()
    total_ingresos = Decimal("0")
    total_costo = Decimal("0")
    for v in ventas:
        total_ingresos += to_decimal(v.total)
        if v.id_orden:
            orden = db.query(OT).filter(OT.id == v.id_orden).first()
            if orden and not getattr(orden, "cliente_proporciono_refacciones", False):
                res = (
                    db.query(func.coalesce(func.sum(MovimientoInventario.costo_total), 0))
                    .filter(
                        MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
                        MovimientoInventario.referencia == orden.numero_orden,
                    )
                    .scalar()
                )
                total_costo += to_decimal(res or 0)
        else:
            res = (
                db.query(func.coalesce(func.sum(MovimientoInventario.costo_total), 0))
                .filter(
                    MovimientoInventario.id_venta == v.id_venta,
                    MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
                )
                .scalar()
            )
            total_costo += to_decimal(res or 0)

    query_cancel = db.query(Venta).filter(Venta.estado == "CANCELADA")
    for cond in condiciones_rango_taller(Venta.fecha, fecha_desde, fecha_hasta):
        query_cancel = query_cancel.filter(cond)
    ids_cancel = [x.id_venta for x in query_cancel.all()]
    perdidas_mer = Decimal("0")
    if ids_cancel:
        res_mer = (
            db.query(func.coalesce(func.sum(CancelacionProducto.costo_total_mer), 0))
            .filter(CancelacionProducto.id_venta.in_(ids_cancel))
            .scalar()
        )
        perdidas_mer = to_decimal(res_mer or 0)
    utilidad_bruta = money_round(total_ingresos - total_costo - perdidas_mer)
    utilidad_neta = float(money_round(utilidad_bruta - to_decimal(total_gastos)))

    # CPP pesado — solo en bloque finanzas
    ordenes_cp = (
        db.query(OrdenCompra)
        .options(joinedload(OrdenCompra.detalles))
        .filter(OrdenCompra.estado.in_([EstadoOrdenCompra.RECIBIDA, EstadoOrdenCompra.RECIBIDA_PARCIAL]))
        .all()
    )
    total_saldo_oc = Decimal("0")
    count_oc = 0
    for oc in ordenes_cp:
        total_a_pagar = Decimal("0")
        for d in oc.detalles:
            cant = float(getattr(d, "cantidad_recibida", 0) or 0)
            if cant <= 0:
                continue
            precio = d.precio_unitario_real if d.precio_unitario_real is not None else d.precio_unitario_estimado
            total_a_pagar += Decimal(str(cant)) * Decimal(str(precio or 0))
        if total_a_pagar <= 0:
            continue
        pagos = db.query(PagoOrdenCompra).filter(PagoOrdenCompra.id_orden_compra == oc.id_orden_compra).all()
        total_pagado = sum(to_decimal(p.monto) for p in pagos)
        saldo = money_round(max(Decimal("0"), total_a_pagar - total_pagado))
        if saldo > 0:
            total_saldo_oc += saldo
            count_oc += 1

    cuentas_man = (
        db.query(CuentaPagarManual)
        .options(joinedload(CuentaPagarManual.pagos))
        .filter(not CuentaPagarManual.cancelada)
        .all()
    )
    total_man = Decimal("0")
    count_man = 0
    for c in cuentas_man:
        total_pagado = sum(to_decimal(p.monto) for p in c.pagos)
        saldo = money_round(max(Decimal("0"), to_decimal(c.monto_total) - total_pagado))
        if saldo > 0:
            total_man += saldo
            count_man += 1

    hoy_dt = hoy_taller()
    mes_ini = f"{hoy_dt.year}-{hoy_dt.month:02d}-01"
    mes_fin = hoy_dt.isoformat()
    devoluciones_mes = query_devoluciones(db, fecha_desde=mes_ini, fecha_hasta=mes_fin).count()

    alertas = None
    if es_admin:
        totales = db.query(
            func.count(CajaAlerta.id_alerta).label("total"),
            func.sum(case((not CajaAlerta.resuelta, 1), else_=0)).label("pendientes"),
            func.sum(case((CajaAlerta.nivel == "CRITICO", 1), else_=0)).label("criticas"),
        ).one()
        alertas = {
            "total": totales.total or 0,
            "pendientes": totales.pendientes or 0,
            "criticas": totales.criticas or 0,
        }

    return {
        "periodo": periodo,
        "total_ventas_periodo": total_ventas_periodo,
        "total_facturado": total_facturado,
        "total_gastos": total_gastos,
        "utilidad_neta": utilidad_neta,
        "cuentas_por_pagar": {
            "total_saldo_pendiente": float(total_saldo_oc + total_man),
            "total_cuentas": count_oc + count_man,
        },
        "devoluciones_mes": devoluciones_mes,
        "alertas": alertas,
    }


@router.get("")
def get_dashboard_agregado(
    secciones: Optional[str] = Query(
        None,
        description="operativa, finanzas, inventario (CSV). Default: operativa",
    ),
    periodo: str = Query("mes", description="mes, mes_pasado, ano, acumulado — requerido con finanzas"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Dashboard V2 — endpoint único con secciones lazy.

    Default: solo bloque operativa (rápido).
    Finanzas e inventario se calculan únicamente si se solicitan.
    """
    try:
        secciones_list = parse_secciones(secciones)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if "finanzas" in secciones_list and periodo not in ("mes", "mes_pasado", "ano", "acumulado"):
        raise HTTPException(status_code=422, detail=f"periodo inválido: {periodo}")

    rol = getattr(current_user.rol, "value", None) or str(getattr(current_user, "rol", ""))
    es_admin = rol == "ADMIN"
    es_admin_o_caja = rol in ("ADMIN", "CAJA")

    meta = {
        "zona": settings.TALLER_TIMEZONE,
        "generado_en": isoformat_utc(datetime.utcnow()),
        "secciones_calculadas": list(secciones_list),
    }

    result: dict = {
        "meta": meta,
        "operativa": None,
        "finanzas": None,
        "inventario": None,
    }

    if not es_admin_o_caja:
        result["clientes"] = db.query(Cliente).count()
        result["ordenes"] = db.query(OrdenTrabajo).count()
        return result

    if "operativa" in secciones_list:
        result["operativa"] = construir_bloque_operativa(db, current_user)

    if "finanzas" in secciones_list:
        result["finanzas"] = _build_finanzas(db, periodo, current_user, es_admin)

    if "inventario" in secciones_list:
        result["inventario"] = _build_inventario(db)

    return result
