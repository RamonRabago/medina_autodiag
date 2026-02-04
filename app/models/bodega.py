"""Modelo Bodega - Almacenes o puntos de almacenamiento"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP
from app.database import Base
import datetime


class Bodega(Base):
    """Bodegas o almacenes (Principal, Taller, Mostrador, etc.)"""
    __tablename__ = "bodegas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
