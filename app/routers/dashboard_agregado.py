"""
Router agregado para Dashboard: un solo endpoint que devuelve todos los datos
que el frontend necesita, reduciendo de 12+ requests a 1.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case

from app.database import get_db
from app.models.cliente import Cliente
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden, PrioridadOrden
from app.models.orden_compra import OrdenCompra, EstadoOrdenCompra
from app.models.proveedor import Proveedor
from app.models.pago import Pago
from app.models.pago_orden_compra import PagoOrdenCompra
from app.models.venta import Venta
from app.models.gasto_operativo import GastoOperativo
from app.models.caja_turno import CajaTurno
from app.models.cita import Cita, EstadoCita
from app.models.caja_alerta import CajaAlerta
from app.models.repuesto import Repuesto
from app.models.alerta_inventario import AlertaInventario
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.cancelacion_producto import CancelacionProducto
from app.models.cuenta_pagar_manual import CuentaPagarManual
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_decimal, money_round, to_float_money
from app.utils.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services.inventario_service import InventarioService
from app.services.gastos_service import query_gastos
from app.services.devoluciones_service import query_devoluciones
from app.services.caja_alertas import generar_alerta_turno_largo

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _get_rango_periodo(periodo: str) -> tuple[Optional[str], Optional[str]]:
    """Retorna (fecha_desde, fecha_hasta) para el periodo indicado."""
    hoy = date.today()
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


@router.get("")
def get_dashboard_agregado(
    periodo: str = Query("mes", description="mes, mes_pasado, ano, acumulado"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Endpoint agregado del Dashboard. Devuelve en una sola respuesta todos los
    datos que el frontend necesita según el rol del usuario.
    """
    rol = getattr(current_user.rol, "value", None) or str(getattr(current_user, "rol", ""))
    es_admin = rol == "ADMIN"
    es_admin_o_caja = rol in ("ADMIN", "CAJA")

    # Siempre: clientes y órdenes
    clientes_total = db.query(Cliente).count()
    ordenes_total = db.query(OrdenTrabajo).count()

    result = {
        "clientes": clientes_total,
        "ordenes": ordenes_total,
        "ordenes_hoy": 0,
        "total_facturado": 0,
        "total_ventas_periodo": 0,
        "ordenes_urgentes": 0,
        "ordenes_por_estado": [],
        "inventario": None,
        "ordenes_compra_alertas": None,
        "cuentas_por_pagar": {"total_saldo_pendiente": 0, "total_cuentas": 0},
        "turno_caja": None,
        "alertas": None,
        "total_gastos_mes": 0,
        "utilidad_neta_mes": 0,
        "citas_proximas": [],
        "devoluciones_mes": 0,
    }

    if not es_admin_o_caja:
        return result

    fecha_desde, fecha_hasta = _get_rango_periodo(periodo) if periodo != "acumulado" else (None, None)

    # Estadísticas órdenes de trabajo
    ordenes_por_estado = db.query(
        OrdenTrabajo.estado,
        func.count(OrdenTrabajo.id).label("total"),
    ).group_by(OrdenTrabajo.estado).all()
    result["ordenes_por_estado"] = [{"estado": e, "total": t} for e, t in ordenes_por_estado]

    hoy_dt = date.today()
    result["ordenes_hoy"] = db.query(func.count(OrdenTrabajo.id)).filter(
        func.date(OrdenTrabajo.fecha_ingreso) == hoy_dt
    ).scalar() or 0

    q_facturado = db.query(func.coalesce(func.sum(Pago.monto), 0)).join(Venta, Pago.id_venta == Venta.id_venta).filter(Venta.estado != "CANCELADA")
    if fecha_desde:
        q_facturado = q_facturado.filter(func.date(Pago.fecha) >= fecha_desde)
    if fecha_hasta:
        q_facturado = q_facturado.filter(func.date(Pago.fecha) <= fecha_hasta)
    result["total_facturado"] = float(q_facturado.scalar() or 0)

    q_ventas = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(Venta.estado != "CANCELADA")
    if fecha_desde:
        q_ventas = q_ventas.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        q_ventas = q_ventas.filter(func.date(Venta.fecha) <= fecha_hasta)
    result["total_ventas_periodo"] = float(q_ventas.scalar() or 0)

    result["ordenes_urgentes"] = db.query(func.count(OrdenTrabajo.id)).filter(
        OrdenTrabajo.prioridad == PrioridadOrden.URGENTE,
        OrdenTrabajo.estado.in_([EstadoOrden.PENDIENTE, EstadoOrden.EN_PROCESO]),
    ).scalar() or 0

    # Inventario dashboard
    valor_inv = InventarioService.calcular_valor_inventario(db)
    total_alertas = db.query(func.count(AlertaInventario.id_alerta)).join(
        Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto
    ).filter(AlertaInventario.activa == True, Repuesto.eliminado == False).scalar() or 0
    sin_stock = db.query(func.count(Repuesto.id_repuesto)).filter(
        Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual == 0
    ).scalar() or 0
    stock_bajo = db.query(func.count(Repuesto.id_repuesto)).filter(
        Repuesto.activo == True, Repuesto.eliminado == False,
        Repuesto.stock_actual <= Repuesto.stock_minimo, Repuesto.stock_actual > 0
    ).scalar() or 0
    productos_activos = db.query(func.count(Repuesto.id_repuesto)).filter(
        Repuesto.activo == True, Repuesto.eliminado == False
    ).scalar() or 0
    result["inventario"] = {
        "valor_inventario": valor_inv,
        "productos_activos": productos_activos,
        "productos_sin_stock": sin_stock,
        "productos_stock_bajo": stock_bajo,
        "total_alertas": total_alertas,
    }

    # Órdenes de compra alertas
    base_oc = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_([EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.RECIBIDA_PARCIAL])
    )
    ordenes_sin_recibir = base_oc.count()
    hoy_dt_dt = datetime.combine(date.today(), datetime.min.time())
    ordenes_vencidas = base_oc.filter(
        OrdenCompra.fecha_estimada_entrega.isnot(None),
        OrdenCompra.fecha_estimada_entrega < hoy_dt_dt,
    ).count()
    result["ordenes_compra_alertas"] = {
        "ordenes_sin_recibir": ordenes_sin_recibir,
        "ordenes_vencidas": ordenes_vencidas,
    }

    # Cuentas por pagar (órdenes compra) - simplificado: total saldo
    ordenes_cp = db.query(OrdenCompra).options(
        joinedload(OrdenCompra.detalles),
    ).filter(
        OrdenCompra.estado.in_([EstadoOrdenCompra.RECIBIDA, EstadoOrdenCompra.RECIBIDA_PARCIAL])
    ).all()
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
    result["cuentas_por_pagar"]["total_saldo_pendiente"] = float(total_saldo_oc)
    result["cuentas_por_pagar"]["total_cuentas"] = count_oc

    # Cuentas manuales
    cuentas_man = db.query(CuentaPagarManual).options(
        joinedload(CuentaPagarManual.pagos),
    ).filter(CuentaPagarManual.cancelada == False).all()
    total_man = Decimal("0")
    count_man = 0
    for c in cuentas_man:
        total_pagado = sum(to_decimal(p.monto) for p in c.pagos)
        saldo = money_round(max(Decimal("0"), to_decimal(c.monto_total) - total_pagado))
        if saldo > 0:
            total_man += saldo
            count_man += 1
    result["cuentas_por_pagar"]["total_saldo_pendiente"] += float(total_man)
    result["cuentas_por_pagar"]["total_cuentas"] += count_man

    # Turno caja
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO",
    ).first()
    if turno:
        generar_alerta_turno_largo(db, turno)
        db.commit()
        result["turno_caja"] = {
            "estado": turno.estado,
            "monto_apertura": float(turno.monto_apertura or 0),
        }

    # Gastos resumen
    q_g = query_gastos(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    result["total_gastos_mes"] = float(q_g.with_entities(func.coalesce(func.sum(GastoOperativo.monto), 0)).scalar() or 0)

    # Utilidad (simplificado: ingresos - costo - gastos)
    from app.models.orden_trabajo import OrdenTrabajo as OT
    query_ventas = db.query(Venta).filter(Venta.estado != "CANCELADA")
    if fecha_desde:
        query_ventas = query_ventas.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query_ventas = query_ventas.filter(func.date(Venta.fecha) <= fecha_hasta)
    ventas = query_ventas.all()
    total_ingresos = Decimal("0")
    total_costo = Decimal("0")
    for v in ventas:
        total_ingresos += to_decimal(v.total)
        if v.id_orden:
            orden = db.query(OT).filter(OT.id == v.id_orden).first()
            if orden and not getattr(orden, "cliente_proporciono_refacciones", False):
                res = db.query(func.coalesce(func.sum(MovimientoInventario.costo_total), 0)).filter(
                    MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
                    MovimientoInventario.referencia == orden.numero_orden,
                ).scalar()
                total_costo += to_decimal(res or 0)
        else:
            res = db.query(func.coalesce(func.sum(MovimientoInventario.costo_total), 0)).filter(
                MovimientoInventario.id_venta == v.id_venta,
                MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
            ).scalar()
            total_costo += to_decimal(res or 0)
    query_cancel = db.query(Venta).filter(Venta.estado == "CANCELADA")
    if fecha_desde:
        query_cancel = query_cancel.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query_cancel = query_cancel.filter(func.date(Venta.fecha) <= fecha_hasta)
    ids_cancel = [x.id_venta for x in query_cancel.all()]
    perdidas_mer = Decimal("0")
    if ids_cancel:
        res_mer = db.query(func.coalesce(func.sum(CancelacionProducto.costo_total_mer), 0)).filter(
            CancelacionProducto.id_venta.in_(ids_cancel)
        ).scalar()
        perdidas_mer = to_decimal(res_mer or 0)
    utilidad_bruta = money_round(total_ingresos - total_costo - perdidas_mer)
    total_gastos_dec = to_decimal(result["total_gastos_mes"])
    result["utilidad_neta_mes"] = float(money_round(utilidad_bruta - total_gastos_dec))

    # Citas próximas
    ahora = datetime.now()
    citas = db.query(Cita).options(
        joinedload(Cita.cliente),
        joinedload(Cita.vehiculo),
    ).filter(
        Cita.estado == EstadoCita.CONFIRMADA,
        Cita.fecha_hora >= ahora,
    ).order_by(Cita.fecha_hora.asc()).limit(8).all()
    items_citas = []
    for c in citas:
        items_citas.append({
            "id_cita": c.id_cita,
            "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else None,
            "cliente_nombre": c.cliente.nombre if c.cliente else None,
        })
    result["citas_proximas"] = items_citas

    # Devoluciones del mes
    mes_ini = f"{hoy_dt.year}-{hoy_dt.month:02d}-01"
    mes_fin = hoy_dt.isoformat()
    q_dev = query_devoluciones(db, fecha_desde=mes_ini, fecha_hasta=mes_fin)
    result["devoluciones_mes"] = q_dev.count()

    # Admin: alertas
    if es_admin:
        totales = db.query(
            func.count(CajaAlerta.id_alerta).label("total"),
            func.sum(case((CajaAlerta.resuelta == False, 1), else_=0)).label("pendientes"),
            func.sum(case((CajaAlerta.nivel == "CRITICO", 1), else_=0)).label("criticas"),
        ).one()
        result["alertas"] = {
            "total": totales.total or 0,
            "pendientes": totales.pendientes or 0,
            "criticas": totales.criticas or 0,
        }

    return result
