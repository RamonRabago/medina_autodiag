"""Modelo Nivel - Niveles de un estante (ej: A, B, C, D)"""

import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String

from app.database import Base


class Nivel(Base):
    """Catálogo global de niveles (vertical)"""

    __tablename__ = "niveles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(50), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)
