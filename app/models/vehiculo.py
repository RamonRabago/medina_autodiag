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
    motor = Column(String(50))
    vin = Column(String(50))
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="vehiculo")
