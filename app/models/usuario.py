from sqlalchemy import Column, Integer, String, Enum, Boolean, TIMESTAMP
from app.database import Base
import datetime

from sqlalchemy.orm import relationship

class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum("ADMIN", "EMPLEADO", "TECNICO","CAJA"), default="TECNICO")
    activo = Column(Boolean, default=True)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    
    ordenes_asignadas = relationship("OrdenTrabajo", back_populates="tecnico")
