from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class CategoriaServicio(Base):
    """Categorías de servicios (Mantenimiento, Reparación, etc.)"""
    __tablename__ = "categorias_servicios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    servicios = relationship("Servicio", back_populates="categoria")
