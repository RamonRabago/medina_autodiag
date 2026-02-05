"""Modelo UsuarioBodega - Bodegas permitidas por usuario (restricción de inventario)"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.database import Base


class UsuarioBodega(Base):
    """
    Tabla asociativa: qué bodegas puede ver un usuario en inventario.
    Si un usuario tiene filas aquí, solo ve repuestos de esas bodegas.
    Si no tiene filas (o es ADMIN), ve todas.
    """
    __tablename__ = "usuario_bodegas"

    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, primary_key=True)
    id_bodega = Column(Integer, ForeignKey("bodegas.id", ondelete="CASCADE"), nullable=False, primary_key=True)
