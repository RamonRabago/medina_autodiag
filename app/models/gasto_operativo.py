"""
Modelo de Gasto Operativo.
Registra gastos del negocio (renta, servicios, material, etc.).
"""
from sqlalchemy import Column, Integer, String, Numeric, Text, Date, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class GastoOperativo(Base):
    __tablename__ = "gastos_operativos"

    id_gasto = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    concepto = Column(String(200), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    categoria = Column(
        Enum("RENTA", "SERVICIOS", "MATERIAL", "NOMINA", "OTROS", "DEVOLUCION_VENTA", name="categoria_gasto"),
        default="OTROS",
        nullable=False,
    )
    id_turno = Column(Integer, ForeignKey("caja_turnos.id_turno"), nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(TIMESTAMP, server_default=func.now())

    usuario = relationship("Usuario")
    turno = relationship("CajaTurno", foreign_keys=[id_turno])
