"""
Router unificado de notificaciones/alertas.
Agrega alertas de caja, inventario y órdenes de compra en una sola respuesta.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, date
from typing import Any

from app.database import get_db
from app.models.caja_alerta import CajaAlerta
from app.models.alerta_inventario import AlertaInventario
from app.models.repuesto import Repuesto
from app.models.orden_compra import OrdenCompra
from app.models.proveedor import Proveedor
from app.models.alerta_inventario import TipoAlertaInventario
from app.models.orden_compra import EstadoOrdenCompra
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario


router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"],
)


def _alertas_caja(db: Session) -> list[dict[str, Any]]:
    """Alertas de caja no resueltas (ADMIN)."""
    alertas = (
        db.query(CajaAlerta)
        .filter(CajaAlerta.resuelta == False)
        .order_by(CajaAlerta.fecha_creacion.desc())
        .all()
    )
    return [
        {
            "id_alerta": a.id_alerta,
            "id_turno": a.id_turno,
            "id_usuario": a.id_usuario,
            "tipo": a.tipo,
            "nivel": a.nivel,
            "mensaje": a.mensaje,
            "resuelta": a.resuelta,
            "fecha_creacion": a.fecha_creacion.isoformat() if a.fecha_creacion else None,
            "fecha_resolucion": a.fecha_resolucion.isoformat() if a.fecha_resolucion else None,
            "resuelta_por": a.resuelta_por,
        }
        for a in alertas
    ]


def _alertas_inventario(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    """Alertas de inventario activas."""
    alertas = (
        db.query(AlertaInventario)
        .join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto)
        .filter(AlertaInventario.activa == True, Repuesto.eliminado == False)
        .options(joinedload(AlertaInventario.repuesto))
        .order_by(AlertaInventario.fecha_creacion.desc())
        .limit(limit)
        .all()
    )
    result = []
    for a in alertas:
        item = {
            "id_alerta": a.id_alerta,
            "id_repuesto": a.id_repuesto,
            "tipo_alerta": a.tipo_alerta.value if hasattr(a.tipo_alerta, "value") else str(a.tipo_alerta),
            "mensaje": a.mensaje,
            "stock_actual": a.stock_actual,
            "stock_minimo": a.stock_minimo,
            "stock_maximo": a.stock_maximo,
            "activa": a.activa,
            "fecha_creacion": a.fecha_creacion.isoformat() if a.fecha_creacion else None,
        }
        if a.repuesto:
            item["repuesto"] = {"codigo": a.repuesto.codigo, "nombre": a.repuesto.nombre}
        else:
            item["repuesto"] = None
        result.append(item)
    return result


def _resumen_inventario(db: Session) -> dict[str, int]:
    """Resumen de alertas de inventario por tipo."""
    alertas = (
        db.query(AlertaInventario.tipo_alerta, func.count(AlertaInventario.id_alerta).label("cantidad"))
        .join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto)
        .filter(AlertaInventario.activa == True, Repuesto.eliminado == False)
        .group_by(AlertaInventario.tipo_alerta)
        .all()
    )
    resumen = {
        "total_alertas": 0,
        "alertas_criticas": 0,
        "alertas_stock_bajo": 0,
        "alertas_sin_stock": 0,
        "alertas_sin_movimiento": 0,
        "alertas_sobre_stock": 0,
    }
    for alerta in alertas:
        tipo = alerta.tipo_alerta.value if hasattr(alerta.tipo_alerta, "value") else str(alerta.tipo_alerta)
        resumen["total_alertas"] += alerta.cantidad
        if tipo == TipoAlertaInventario.STOCK_CRITICO.value:
            resumen["alertas_criticas"] = alerta.cantidad
        elif tipo == TipoAlertaInventario.STOCK_BAJO.value:
            resumen["alertas_stock_bajo"] = alerta.cantidad
        elif tipo == TipoAlertaInventario.SIN_STOCK.value:
            resumen["alertas_sin_stock"] = alerta.cantidad
        elif tipo == TipoAlertaInventario.SIN_MOVIMIENTO.value:
            resumen["alertas_sin_movimiento"] = alerta.cantidad
        elif tipo == TipoAlertaInventario.SOBRE_STOCK.value:
            resumen["alertas_sobre_stock"] = alerta.cantidad
    return resumen


def _ordenes_compra_alertas(db: Session, limit: int = 15) -> dict[str, Any]:
    """Órdenes pendientes de recibir para ADMIN/CAJA."""
    hoy = datetime.utcnow().date()
    base = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_([
            EstadoOrdenCompra.ENVIADA,
            EstadoOrdenCompra.RECIBIDA_PARCIAL,
        ])
    )
    ordenes_sin_recibir = base.count()
    hoy_dt = datetime.combine(hoy, datetime.min.time())
    ordenes_vencidas = base.filter(
        OrdenCompra.fecha_estimada_entrega.isnot(None),
        OrdenCompra.fecha_estimada_entrega < hoy_dt,
    ).count()

    ordenes = (
        base.order_by(
            func.coalesce(OrdenCompra.fecha_estimada_entrega, datetime(9999, 12, 31)).asc()
        )
        .limit(limit * 3)
        .all()
    )

    items = []
    for oc in ordenes:
        fecha_est = getattr(oc, "fecha_estimada_entrega", None)
        vencida = False
        if fecha_est:
            try:
                fecha_est_date = fecha_est.date() if hasattr(fecha_est, "date") else fecha_est
                vencida = fecha_est_date < hoy
            except (AttributeError, TypeError):
                pass

        prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
        items.append({
            "id_orden_compra": oc.id_orden_compra,
            "numero": oc.numero,
            "nombre_proveedor": prov.nombre if prov else "",
            "estado": oc.estado.value if hasattr(oc.estado, "value") else str(oc.estado),
            "fecha_estimada_entrega": fecha_est.isoformat()[:10] if fecha_est else None,
            "vencida": vencida,
            "total_estimado": float(oc.total_estimado or 0),
        })

    items.sort(key=lambda x: (0 if x["vencida"] else 1, x["fecha_estimada_entrega"] or "9999"))
    items = items[:limit]

    return {
        "ordenes_sin_recibir": ordenes_sin_recibir,
        "ordenes_vencidas": ordenes_vencidas,
        "items": items,
    }


@router.get("", include_in_schema=False)
@router.get("/")
def listar_notificaciones(
    limit_inventario: int = Query(50, ge=1, le=100),
    limit_ordenes: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Agrega todas las notificaciones/alertas según el rol del usuario.

    - **ADMIN**: alertas de caja + inventario + órdenes de compra
    - **CAJA**: inventario + órdenes de compra
    - **Otros**: solo inventario

    Respuesta: alertas_caja, alertas_inventario, resumen_inventario, ordenes_compra, total_alertas
    """
    rol = current_user.rol.value if hasattr(current_user.rol, "value") else str(current_user.rol)

    alertas_caja = []
    if rol == "ADMIN":
        alertas_caja = _alertas_caja(db)

    alertas_inventario = _alertas_inventario(db, limit=limit_inventario)
    resumen_inventario = _resumen_inventario(db)

    ordenes_compra = None
    if rol in ("ADMIN", "CAJA"):
        ordenes_compra = _ordenes_compra_alertas(db, limit=limit_ordenes)

    total_alertas = (
        len(alertas_caja) +
        len(alertas_inventario) +
        (1 if ordenes_compra and ordenes_compra.get("ordenes_sin_recibir", 0) > 0 else 0)
    )

    return {
        "alertas_caja": alertas_caja,
        "alertas_inventario": alertas_inventario,
        "resumen_inventario": resumen_inventario,
        "ordenes_compra": ordenes_compra,
        "total_alertas": total_alertas,
    }


@router.get("/count")
def count_notificaciones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Devuelve solo el total de alertas pendientes (para badge en menú).

    Respuesta: { "total_alertas": int }
    """
    rol = current_user.rol.value if hasattr(current_user.rol, "value") else str(current_user.rol)

    count_caja = 0
    if rol == "ADMIN":
        count_caja = db.query(CajaAlerta).filter(CajaAlerta.resuelta == False).count()

    count_inventario = (
        db.query(AlertaInventario)
        .join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto)
        .filter(AlertaInventario.activa == True, Repuesto.eliminado == False)
        .count()
    )

    count_ordenes = 0
    if rol in ("ADMIN", "CAJA"):
        count_ordenes = (
            db.query(OrdenCompra)
            .filter(OrdenCompra.estado.in_([
                EstadoOrdenCompra.ENVIADA,
                EstadoOrdenCompra.RECIBIDA_PARCIAL,
            ]))
            .count()
        )

    total = count_caja + count_inventario + (1 if count_ordenes > 0 else 0)
    return {"total_alertas": total}
