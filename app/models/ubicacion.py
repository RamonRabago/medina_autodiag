"""Modelo Ubicación - Posiciones dentro de una bodega (ej: Pasillo A-1, Estante B2)"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class Ubicacion(Base):
    """Ubicaciones dentro de cada bodega (Pasillo, Estante, Nivel, etc.)"""
    __tablename__ = "ubicaciones"
    __table_args__ = (UniqueConstraint("id_bodega", "codigo", name="uq_bodega_codigo"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_bodega = Column(Integer, ForeignKey("bodegas.id"), nullable=False, index=True)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    bodega = relationship("Bodega", backref="ubicaciones")

    @property
    def bodega_nombre(self):
        return self.bodega.nombre if self.bodega else ""
