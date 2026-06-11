import datetime

from sqlalchemy import TIMESTAMP, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CategoriaRepuesto(Base):
    __tablename__ = "categorias_repuestos"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    # Relación con repuestos
    repuestos = relationship("Repuesto", back_populates="categoria")
