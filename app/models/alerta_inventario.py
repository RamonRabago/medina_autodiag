from sqlalchemy import Column, Integer, Numeric, String, Text, TIMESTAMP, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import datetime
import enum

class TipoAlertaInventario(str, enum.Enum):
    STOCK_BAJO = "STOCK_BAJO"        # Stock alcanzó el mínimo
    STOCK_CRITICO = "STOCK_CRITICO"  # Stock por debajo del mínimo
    SIN_STOCK = "SIN_STOCK"          # Stock en 0
    SIN_MOVIMIENTO = "SIN_MOVIMIENTO" # Sin movimientos por mucho tiempo
    SOBRE_STOCK = "SOBRE_STOCK"      # Stock superior al máximo

class AlertaInventario(Base):
    __tablename__ = "alertas_inventario"

    id_alerta = Column(Integer, primary_key=True, index=True)
    
    # Relación con repuesto
    id_repuesto = Column(Integer, ForeignKey("repuestos.id_repuesto"), nullable=False)
    
    # Tipo de alerta
    tipo_alerta = Column(Enum(TipoAlertaInventario), nullable=False)
    
    # Información de la alerta
    mensaje = Column(Text, nullable=False)
    stock_actual = Column(Numeric(10, 3))
    stock_minimo = Column(Numeric(10, 3))
    stock_maximo = Column(Numeric(10, 3))
    
    # Estado
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    fecha_resolucion = Column(TIMESTAMP)
    resuelto_por = Column(Integer, ForeignKey("usuarios.id_usuario"))
    
    # Relaciones
    repuesto = relationship("Repuesto")
    usuario_resolucion = relationship("Usuario")
