"""Schemas para Ubicación"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class UbicacionBase(BaseModel):
    id_bodega: int = Field(..., description="ID de la bodega")
    codigo: str = Field(..., min_length=1, max_length=50, description="Código (ej: A1, B2)")
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    activo: bool = Field(default=True)


class UbicacionCreate(UbicacionBase):
    pass


class UbicacionUpdate(BaseModel):
    id_bodega: Optional[int] = None
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    activo: Optional[bool] = None


class UbicacionOut(UbicacionBase):
    id: int
    creado_en: datetime | None = None
    bodega_nombre: str = ""
    model_config = ConfigDict(from_attributes=True)
