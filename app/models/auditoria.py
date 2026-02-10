"""
Registro de auditoría: acciones de usuarios sobre módulos (órdenes de compra, pagos, etc.).
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id_auditoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    modulo = Column(String(80), nullable=False)
    accion = Column(String(50), nullable=False)
    id_referencia = Column(Integer, nullable=True)
    descripcion = Column(Text, nullable=True)
    fecha = Column(DateTime, nullable=False, server_default=func.now())

    usuario = relationship("Usuario", lazy="joined")
