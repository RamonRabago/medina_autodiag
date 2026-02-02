from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import datetime
import enum

class TipoMovimiento(str, enum.Enum):
    ENTRADA = "ENTRADA"          # Compra o devolución
    SALIDA = "SALIDA"            # Venta o uso en servicio
    AJUSTE_POSITIVO = "AJUSTE+"  # Corrección de inventario al alza
    AJUSTE_NEGATIVO = "AJUSTE-"  # Corrección de inventario a la baja
    MERMA = "MERMA"              # Pérdida o daño

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id_movimiento = Column(Integer, primary_key=True, index=True)
    
    # Relación con repuesto
    id_repuesto = Column(Integer, ForeignKey("repuestos.id_repuesto"), nullable=False)
    
    # Tipo de movimiento
    tipo_movimiento = Column(Enum(TipoMovimiento), nullable=False)
    
    # Cantidad y valores
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(DECIMAL(10, 2))
    costo_total = Column(DECIMAL(10, 2))
    
    # Stock antes y después del movimiento
    stock_anterior = Column(Integer, nullable=False)
    stock_nuevo = Column(Integer, nullable=False)
    
    # Información del movimiento
    referencia = Column(String(100))  # Número de factura, orden de trabajo, etc.
    motivo = Column(Text)
    
    # Relaciones opcionales
    id_venta = Column(Integer, ForeignKey("ventas.id_venta"))  # Si es una salida por venta
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))  # Usuario que realizó el movimiento
    
    # Fechas
    fecha_movimiento = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    # Relaciones
    repuesto = relationship("Repuesto", back_populates="movimientos")
    usuario = relationship("Usuario")
