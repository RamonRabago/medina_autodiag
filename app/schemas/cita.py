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


class CitaEstadoPatchRequest(BaseModel):
    estado_nuevo: str
    motivo_codigo: Optional[str] = None
    motivo_detalle: Optional[str] = None
    motivo_cancelacion: Optional[str] = None


class CitaEstadoMetaOut(BaseModel):
    transiciones_permitidas: list[str] = Field(default_factory=list)
    requiere_motivo: bool = False
    estado_editable: bool = False
    ventana_activa: bool = False
    tiene_ot: bool = False
    bloqueo_financiero: bool = False


class CitaEstadoHistorialOut(BaseModel):
    id: int
    id_cita: int
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    motivo_codigo: Optional[str] = None
    motivo_detalle: Optional[str] = None
    id_usuario: int
    id_orden: Optional[int] = None
    origen: str
    creado_en: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CitaEstadoPatchResponse(BaseModel):
    id_cita: int
    estado: str
    estado_origen_cierre: Optional[str] = None
    motivo_cancelacion: Optional[str] = None
    id_orden: Optional[int] = None
    ultimo_evento: CitaEstadoHistorialOut
    estado_meta: CitaEstadoMetaOut
