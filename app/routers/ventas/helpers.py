"""Helpers compartidos para el módulo de ventas."""
from sqlalchemy.orm import Session

from app.models.detalle_venta import DetalleVenta
from app.models.repuesto import Repuesto


def serializar_detalles_venta(db: Session, detalles: list) -> list:
    resultado = []
    for d in detalles:
        tipo_str = d.tipo.value if hasattr(d.tipo, "value") else str(d.tipo)
        item = {
            "id_detalle": d.id_detalle,
            "tipo": tipo_str,
            "id_item": d.id_item,
            "descripcion": d.descripcion,
            "cantidad": d.cantidad,
            "precio_unitario": float(d.precio_unitario or 0),
            "subtotal": float(d.subtotal),
        }
        if tipo_str == "PRODUCTO":
            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == d.id_item).first()
            item["es_consumible"] = bool(getattr(rep, "es_consumible", False))
        resultado.append(item)
    return resultado
