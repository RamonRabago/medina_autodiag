"""Busca venta con orden que tenga repuestos para probar cancelación."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.venta import Venta
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleRepuestoOrden

db = SessionLocal()
# Todas las ventas con orden
ventas = db.query(Venta).filter(Venta.id_orden.isnot(None), Venta.estado.in_(["PAGADA", "PENDIENTE"])).all()
print(f"Ventas con orden: {len(ventas)}")
for v in ventas[:5]:
    dets = db.query(DetalleRepuestoOrden).filter(DetalleRepuestoOrden.orden_trabajo_id == v.id_orden).all()
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == v.id_orden).first()
    cp = getattr(orden, "cliente_proporciono_refacciones", False) if orden else False
    print(f"  Venta {v.id_venta}, Orden {v.id_orden}, repuestos={len(dets)}, cliente_provee={cp}")
db.close()
