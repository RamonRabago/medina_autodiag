import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id_proveedor = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    contacto = Column(String(100))
    telefono = Column(String(20))
    email = Column(String(100))
    direccion = Column(Text)
    rfc = Column(String(13))
    activo = Column(Boolean, default=True)
    creado_en = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    # Relación con repuestos
    repuestos = relationship("Repuesto", back_populates="proveedor")
