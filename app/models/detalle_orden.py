# app/models/detalle_orden.py
from decimal import Decimal
from sqlalchemy import Column, Integer, Numeric, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class DetalleOrdenTrabajo(Base):
    """
    Detalle de servicios realizados en una orden de trabajo
    Cada servicio aplicado al vehículo
    """
    __tablename__ = "detalles_orden_trabajo"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    orden_trabajo_id = Column(Integer, ForeignKey("ordenes_trabajo.id", ondelete="CASCADE"), nullable=False, index=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    
    # Detalles del servicio en la orden
    descripcion = Column(String(500), nullable=True)  # Puede personalizar la descripción
    precio_unitario = Column(Numeric(10, 2), nullable=False)  # Precio al momento de la orden
    cantidad = Column(Integer, nullable=False, default=1)
    descuento = Column(Numeric(10, 2), nullable=False, default=0.00)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Tiempo real empleado
    tiempo_real_minutos = Column(Integer, nullable=True)  # Tiempo que realmente se tardó
    observaciones = Column(Text, nullable=True)
    
    # Relaciones
    orden = relationship("OrdenTrabajo", back_populates="detalles_servicio")
    servicio = relationship("Servicio", back_populates="detalles_orden")

    def calcular_subtotal(self):
        """Calcula el subtotal del servicio"""
        p = Decimal(str(self.precio_unitario or 0))
        c = int(self.cantidad or 0)
        d = Decimal(str(self.descuento or 0))
        self.subtotal = (p * c) - d
        return self.subtotal

    def __repr__(self):
        return f"<DetalleOrdenTrabajo(orden_id={self.orden_trabajo_id}, servicio_id={self.servicio_id}, subtotal={self.subtotal})>"


class DetalleRepuestoOrden(Base):
    """
    Detalle de repuestos utilizados en una orden de trabajo
    Vincula la orden con el inventario de repuestos
    """
    __tablename__ = "detalles_repuesto_orden"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    orden_trabajo_id = Column(Integer, ForeignKey("ordenes_trabajo.id", ondelete="CASCADE"), nullable=False, index=True)
    repuesto_id = Column(Integer, ForeignKey("repuestos.id_repuesto"), nullable=False, index=True)
    
    # Detalles del repuesto en la orden
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Numeric(10, 2), nullable=False)  # Precio de venta al momento (0 si cliente provee)
    cliente_provee = Column(Boolean, nullable=False, default=False)  # True = cliente trae la refacción, False = nosotros proveemos
    descuento = Column(Numeric(10, 2), nullable=False, default=0.00)
    subtotal = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    observaciones = Column(Text, nullable=True)
    
    # Relaciones
    orden = relationship("OrdenTrabajo", back_populates="detalles_repuesto")
    repuesto = relationship("Repuesto", back_populates="detalles_orden")

    def calcular_subtotal(self):
        """Calcula el subtotal del repuesto"""
        p = Decimal(str(self.precio_unitario or 0))
        c = int(self.cantidad or 0)
        d = Decimal(str(self.descuento or 0))
        self.subtotal = (p * c) - d
        return self.subtotal

    def __repr__(self):
        return f"<DetalleRepuestoOrden(orden_id={self.orden_trabajo_id}, repuesto_id={self.repuesto_id}, cantidad={self.cantidad})>"
