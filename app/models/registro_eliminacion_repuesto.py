"""Modelo para registrar eliminaciones permanentes de repuestos (auditoría)"""

import datetime

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, Text

from app.database import Base


class RegistroEliminacionRepuesto(Base):
    __tablename__ = "registro_eliminacion_repuesto"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_repuesto = Column(Integer, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    motivo = Column(Text, nullable=False)
    datos_repuesto = Column(Text, nullable=True)  # JSON: codigo, nombre, stock, precios, etc.
    fecha = Column(TIMESTAMP, default=datetime.datetime.utcnow, nullable=False)
