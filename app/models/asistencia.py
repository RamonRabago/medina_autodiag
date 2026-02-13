"""Registro de asistencia día por día - Checador Fase 3."""
from sqlalchemy import Column, Integer, Date, Enum, Numeric, Boolean, Text
from app.database import Base


class TipoAsistencia:
    TRABAJO = "TRABAJO"
    FESTIVO = "FESTIVO"
    VACACION = "VACACION"
    PERMISO_CON_GOCE = "PERMISO_CON_GOCE"
    PERMISO_SIN_GOCE = "PERMISO_SIN_GOCE"
    INCAPACIDAD = "INCAPACIDAD"
    FALTA = "FALTA"


TIPOS_ASISTENCIA = (
    TipoAsistencia.TRABAJO,
    TipoAsistencia.FESTIVO,
    TipoAsistencia.VACACION,
    TipoAsistencia.PERMISO_CON_GOCE,
    TipoAsistencia.PERMISO_SIN_GOCE,
    TipoAsistencia.INCAPACIDAD,
    TipoAsistencia.FALTA,
)


class Asistencia(Base):
    """Registro de asistencia por empleado y fecha."""
    __tablename__ = "asistencia"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, nullable=False, index=True)  # FK usuarios.id_usuario
    fecha = Column(Date, nullable=False, index=True)
    tipo = Column(
        Enum(*TIPOS_ASISTENCIA),
        nullable=False,
        default=TipoAsistencia.TRABAJO
    )
    horas_trabajadas = Column(Numeric(4, 2), nullable=True, default=0)
    turno_completo = Column(Boolean, nullable=True, default=True)
    aplica_bono_puntualidad = Column(Boolean, nullable=True, default=True)
    observaciones = Column(Text, nullable=True)
    id_referencia = Column(Integer, nullable=True)  # Opcional: link a solicitud permiso/vacaciones
