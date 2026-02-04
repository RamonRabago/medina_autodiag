"""Schemas para Estante"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EstanteBase(BaseModel):
    id_ubicacion: int = Field(..., description="ID de la ubicación (zona/pasillo)")
    codigo: str = Field(..., min_length=1, max_length=50, description="Código (ej: E1, E2)")
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    activo: bool = Field(default=True)


class EstanteCreate(EstanteBase):
    pass


class EstanteUpdate(BaseModel):
    id_ubicacion: Optional[int] = None
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    activo: Optional[bool] = None


class EstanteOut(EstanteBase):
    id: int
    creado_en: datetime | None = None
    bodega_nombre: str = ""
    ubicacion_nombre: str = ""

    class Config:
        from_attributes = True
