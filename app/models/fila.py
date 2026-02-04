"""Modelo Fila - Filas/posiciones horizontales (ej: 1, 2, 3, 4, 5)"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from app.database import Base
import datetime


class Fila(Base):
    """Catálogo global de filas (horizontal)"""
    __tablename__ = "filas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(50), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
