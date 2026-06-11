"""Modelo para registrar eliminaciones de vehículos (auditoría)"""

import datetime

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, Text

from app.database import Base


class RegistroEliminacionVehiculo(Base):
    __tablename__ = "registro_eliminacion_vehiculo"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_vehiculo = Column(Integer, nullable=False)  # ID antes de borrar
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    motivo = Column(Text, nullable=False)
    datos_vehiculo = Column(Text, nullable=True)  # JSON: marca, modelo, anio, cliente, etc.
    fecha = Column(TIMESTAMP, default=datetime.datetime.utcnow, nullable=False)
