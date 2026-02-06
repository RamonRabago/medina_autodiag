"""
Compatibilidad repuesto-vehículo (construcción manual).
Permite indicar qué repuestos aplican a qué vehículos (marca, modelo, año).
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class RepuestoCompatibilidad(Base):
    __tablename__ = "repuesto_compatibilidad"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_repuesto = Column(Integer, ForeignKey("repuestos.id_repuesto", ondelete="CASCADE"), nullable=False)

    marca = Column(String(80), nullable=False)
    modelo = Column(String(80), nullable=False)
    anio_desde = Column(Integer, nullable=True)   # null = sin límite inferior
    anio_hasta = Column(Integer, nullable=True)   # null = sin límite superior
    motor = Column(String(50), nullable=True)     # opcional: "1.8", "2.0 Turbo"

    repuesto = relationship("Repuesto", back_populates="compatibilidades")
