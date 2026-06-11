"""Schemas para Bodega"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BodegaBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre de la bodega")
    descripcion: Optional[str] = Field(None, max_length=500)
    activo: bool = Field(default=True)


class BodegaCreate(BodegaBase):
    pass


class BodegaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    activo: Optional[bool] = None


class BodegaOut(BodegaBase):
    id: int
    creado_en: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
