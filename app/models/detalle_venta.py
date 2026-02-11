from sqlalchemy import Column, Integer, DECIMAL, Numeric, String, Enum, ForeignKey
from app.database import Base

class DetalleVenta(Base):
    __tablename__ = "detalle_venta"

    id_detalle = Column(Integer, primary_key=True, index=True)
    id_venta = Column(Integer, ForeignKey("ventas.id_venta", ondelete="CASCADE"))
    tipo = Column(Enum("PRODUCTO","SERVICIO"), nullable=False)
    id_item = Column(Integer, nullable=False)
    descripcion = Column(String(150))
    cantidad = Column(Numeric(10, 3), default=1)
    precio_unitario = Column(DECIMAL(10,2), nullable=False)
    subtotal = Column(DECIMAL(10,2), nullable=False)
    id_orden_origen = Column(Integer, nullable=True, index=True)
