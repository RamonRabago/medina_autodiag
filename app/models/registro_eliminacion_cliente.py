"""Modelo para registrar eliminaciones de clientes (auditoría)"""

import datetime

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, Text

from app.database import Base


class RegistroEliminacionCliente(Base):
    __tablename__ = "registro_eliminacion_cliente"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_cliente = Column(Integer, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    motivo = Column(Text, nullable=False)
    datos_cliente = Column(Text, nullable=True)  # JSON: nombre, telefono, etc.
    fecha = Column(TIMESTAMP, default=datetime.datetime.utcnow, nullable=False)
