"""Schemas para Citas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class CitaBase(BaseModel):
    id_cliente: int
    id_vehiculo: Optional[int] = None
    fecha_hora: datetime
    tipo: str = "REVISION"
    motivo: Optional[str] = None
    notas: Optional[str] = None


class CitaCreate(CitaBase):
    pass


class CitaUpdate(BaseModel):
    id_vehiculo: Optional[int] = None
    fecha_hora: Optional[datetime] = None
    tipo: Optional[str] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None
    motivo_cancelacion: Optional[str] = None  # Requerido cuando estado=CANCELADA
    notas: Optional[str] = None


class CitaOut(BaseModel):
    id_cita: int
    id_cliente: int
    id_vehiculo: Optional[int] = None
    fecha_hora: datetime
    tipo: str
    estado: str
    motivo: Optional[str] = None
    motivo_cancelacion: Optional[str] = None
    notas: Optional[str] = None
    id_orden: Optional[int] = None
    creado_en: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ClienteInasistenciasOut(BaseModel):
    id_cliente: int
    nombre: str
    total_no_asistencias: int


class ReporteAsistenciaCitasOut(BaseModel):
    """Base para reportes de asistencia / no-show en citas."""
    total: int
    confirmadas: int
    asistidas: int
    no_asistidas: int
    canceladas: int
    porcentaje_no_asistencia: float = Field(
        description="no_asistidas / (asistidas + no_asistidas) × 100; 0 si no hay citas cerradas por asistencia.",
    )
    clientes_mayor_inasistencia: list[ClienteInasistenciasOut] = Field(default_factory=list)
