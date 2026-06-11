"""Modelo Bodega - Almacenes o puntos de almacenamiento"""

import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String, Text

from app.database import Base


class Bodega(Base):
    """Bodegas o almacenes (Principal, Taller, Mostrador, etc.)"""

    __tablename__ = "bodegas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    # Relación con ubicaciones (backref en Ubicacion)
