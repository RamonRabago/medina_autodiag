"""Modelo para registrar eliminaciones de clientes (auditoría)"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from app.database import Base
import datetime


class RegistroEliminacionCliente(Base):
    __tablename__ = "registro_eliminacion_cliente"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_cliente = Column(Integer, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True)
    motivo = Column(Text, nullable=False)
    datos_cliente = Column(Text, nullable=True)  # JSON: nombre, telefono, etc.
    fecha = Column(TIMESTAMP, default=datetime.datetime.utcnow, nullable=False)
