"""Schemas para Citas."""
from pydantic import BaseModel, Field
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

    class Config:
        from_attributes = True
