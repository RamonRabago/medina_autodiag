from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from app.database import Base
import datetime

from sqlalchemy.orm import relationship

class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id_vehiculo = Column(Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente", ondelete="CASCADE"))
    marca = Column(String(50))
    modelo = Column(String(50))
    anio = Column(Integer)
    color = Column(String(30))   # Color del vehículo
    motor = Column(String(50))   # Motor/desplazamiento (ej. 1.8)
    vin = Column(String(50))
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="vehiculo")

    @property
    def numero_serie(self):
        """Alias para compatibilidad con API (schema usa numero_serie)."""
        return self.vin
