"""
Órdenes de compra a proveedores.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class EstadoOrdenCompra(str, enum.Enum):
    BORRADOR = "BORRADOR"
    AUTORIZADA = "AUTORIZADA"  # Cotización recibida y aprobada
    ENVIADA = "ENVIADA"
    RECIBIDA_PARCIAL = "RECIBIDA_PARCIAL"
    RECIBIDA = "RECIBIDA"
    CANCELADA = "CANCELADA"


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id_orden_compra = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero = Column(String(50), unique=True, nullable=False, index=True)  # OC-YYYYMMDD-001

    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_vehiculo = Column(Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=True)  # Legacy
    id_catalogo_vehiculo = Column(Integer, ForeignKey("catalogo_vehiculos.id"), nullable=True)  # Catálogo (órdenes de compra)

    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_envio = Column(DateTime, nullable=True)
    fecha_recepcion = Column(DateTime, nullable=True)
    fecha_estimada_entrega = Column(DateTime, nullable=True)  # Fecha estimada de llegada de la mercancía

    estado = Column(Enum(EstadoOrdenCompra), nullable=False, default=EstadoOrdenCompra.BORRADOR)

    total_estimado = Column(Numeric(12, 2), default=0)
    observaciones = Column(Text, nullable=True)
    referencia_proveedor = Column(String(100), nullable=True)  # Nº que asignó el proveedor
    comprobante_url = Column(String(500), nullable=True)  # Imagen o PDF del comprobante de compra

    # Auditoría cancelación
    motivo_cancelacion = Column(Text, nullable=True)
    fecha_cancelacion = Column(DateTime, nullable=True)
    id_usuario_cancelacion = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)

    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proveedor = relationship("Proveedor")
    usuario = relationship("Usuario", foreign_keys=[id_usuario])
    vehiculo = relationship("Vehiculo")
    catalogo_vehiculo = relationship("CatalogoVehiculo")
    detalles = relationship("DetalleOrdenCompra", back_populates="orden_compra", cascade="all, delete-orphan")


class DetalleOrdenCompra(Base):
    __tablename__ = "detalles_orden_compra"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_orden_compra = Column(Integer, ForeignKey("ordenes_compra.id_orden_compra", ondelete="CASCADE"), nullable=False)
    id_repuesto = Column(Integer, ForeignKey("repuestos.id_repuesto"), nullable=True)  # Null cuando es repuesto nuevo (codigo_nuevo, nombre_nuevo)

    codigo_nuevo = Column(String(100), nullable=True)  # Para repuestos que aún no existen en inventario
    nombre_nuevo = Column(String(200), nullable=True)

    cantidad_solicitada = Column(Integer, nullable=False)
    cantidad_recibida = Column(Integer, default=0, nullable=False)
    precio_unitario_estimado = Column(Numeric(10, 2), nullable=False)
    precio_unitario_real = Column(Numeric(10, 2), nullable=True)  # Al recibir, si difiere

    orden_compra = relationship("OrdenCompra", back_populates="detalles")
    repuesto = relationship("Repuesto")
