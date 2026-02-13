"""Días festivos - Checador Fase 2. Admin los define manualmente."""
from sqlalchemy import Column, Integer, String, Date
from app.database import Base


class Festivo(Base):
    __tablename__ = "festivos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fecha = Column(Date, nullable=False)
    nombre = Column(String(100), nullable=False)
    anio = Column(Integer, nullable=False)  # Para filtrar por año
