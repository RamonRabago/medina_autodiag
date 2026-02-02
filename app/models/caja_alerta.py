from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Numeric
)
from sqlalchemy.sql import func
from app.database import Base


class CajaAlerta(Base):
    __tablename__ = "caja_alertas"

    id_alerta = Column(Integer, primary_key=True, index=True)

    id_turno = Column(Integer, ForeignKey("caja_turnos.id_turno"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)

    tipo = Column(String(50), nullable=False)
    nivel = Column(String(20), nullable=False)

    mensaje = Column(String(255), nullable=False)

    diferencia = Column(Numeric(10, 2), nullable=True)

    fecha_creacion = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    resuelta = Column(Boolean, nullable=False, default=False)

    fecha_resolucion = Column(DateTime, nullable=True)

    resuelta_por = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
