"""Modelo de Cita (appointment) para el taller."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import datetime


class TipoCita(str, enum.Enum):
    REVISION = "REVISION"
    MANTENIMIENTO = "MANTENIMIENTO"
    REPARACION = "REPARACION"
    DIAGNOSTICO = "DIAGNOSTICO"
    OTRO = "OTRO"


class EstadoCita(str, enum.Enum):
    CONFIRMADA = "CONFIRMADA"   # Al crear: cliente ya confirmó que vendrá
    SI_ASISTIO = "SI_ASISTIO"   # Cliente asistió
    NO_ASISTIO = "NO_ASISTIO"   # Cliente no se presentó
    CANCELADA = "CANCELADA"     # Cliente avisó que no podrá (con motivo)


class Cita(Base):
    __tablename__ = "citas"

    id_cita = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False, index=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculos.id_vehiculo"), nullable=True, index=True)
    fecha_hora = Column(DateTime, nullable=False, index=True)
    tipo = Column(SQLEnum(TipoCita), nullable=False, default=TipoCita.REVISION)
    estado = Column(SQLEnum(EstadoCita), nullable=False, default=EstadoCita.CONFIRMADA, index=True)
    motivo = Column(String(300), nullable=True)
    motivo_cancelacion = Column(Text, nullable=True)  # Motivo cuando estado=CANCELADA
    notas = Column(Text, nullable=True)
    id_orden = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True, index=True)
    creado_en = Column(DateTime, default=datetime.datetime.utcnow)

    cliente = relationship("Cliente", backref="citas")
    vehiculo = relationship("Vehiculo", backref="citas")
    orden = relationship("OrdenTrabajo", backref="citas")
