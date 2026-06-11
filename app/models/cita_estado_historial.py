"""Historial append-only de transiciones de estado en citas."""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CitaEstadoHistorial(Base):
    __tablename__ = "cita_estado_historial"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_cita = Column(Integer, ForeignKey("citas.id_cita"), nullable=False, index=True)
    estado_anterior = Column(String(20), nullable=True)
    estado_nuevo = Column(String(20), nullable=False)
    motivo_codigo = Column(String(40), nullable=True)
    motivo_detalle = Column(Text, nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_orden = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True)
    origen = Column(String(30), nullable=False)
    creado_en = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    cita = relationship("Cita", backref="historial_estados")
    usuario = relationship("Usuario", lazy="joined")
