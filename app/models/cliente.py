from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from app.database import Base
import datetime

from sqlalchemy.orm import relationship

class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    telefono = Column(String(20))
    email = Column(String(100))
    direccion = Column(Text)
    rfc = Column(String(13))
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="cliente")
