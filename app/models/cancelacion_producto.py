"""Modelo para registrar decisiones por producto al cancelar ventas pagadas (REUTILIZABLE vs MERMA)."""
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class CancelacionProducto(Base):
    __tablename__ = "cancelaciones_productos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_venta = Column(Integer, ForeignKey("ventas.id_venta", ondelete="CASCADE"), nullable=False)
    id_detalle_venta = Column(Integer, ForeignKey("detalle_venta.id_detalle", ondelete="SET NULL"), nullable=True)
    id_repuesto = Column(Integer, ForeignKey("repuestos.id_repuesto"), nullable=False)
    cantidad_reutilizable = Column(Numeric(10, 3), nullable=False, default=0)
    cantidad_mer = Column(Numeric(10, 3), nullable=False, default=0)
    motivo_mer = Column(String(500), nullable=True)
    costo_unitario = Column(Numeric(10, 2), nullable=True)
    costo_total_mer = Column(Numeric(10, 2), nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True)
    fecha = Column(DateTime, server_default=func.now(), nullable=True)
