"""Modelo Estante - Estantes dentro de una ubicación (zona/pasillo)"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class Estante(Base):
    """Estantes dentro de cada ubicación (Bodega → Ubicación → Estante → Nivel → Fila)"""
    __tablename__ = "estantes"
    __table_args__ = (UniqueConstraint("id_ubicacion", "codigo", name="uq_estante_ubicacion_codigo"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_ubicacion = Column(Integer, ForeignKey("ubicaciones.id"), nullable=False, index=True)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    ubicacion = relationship("Ubicacion", backref="estantes")

    @property
    def bodega_nombre(self):
        return self.ubicacion.bodega.nombre if self.ubicacion and self.ubicacion.bodega else ""

    @property
    def ubicacion_nombre(self):
        return f"{self.ubicacion.codigo} - {self.ubicacion.nombre}" if self.ubicacion else ""
