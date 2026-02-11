from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class CajaTurno(Base):
    __tablename__ = "caja_turnos"

    id_turno = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)

    fecha_apertura = Column(DateTime, server_default=func.now())
    fecha_cierre = Column(DateTime, nullable=True)

    monto_apertura = Column(Numeric(10, 2), nullable=False)
    monto_cierre = Column(Numeric(10, 2), nullable=True)
    diferencia = Column(Numeric(10, 2), nullable=True)  # monto_cierre - efectivo_esperado

    estado = Column(
        Enum("ABIERTO", "CERRADO", name="estado_turno"),
        default="ABIERTO"
    )

    usuario = relationship("Usuario")
