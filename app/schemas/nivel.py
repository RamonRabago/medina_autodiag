"""Schemas para Nivel"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NivelBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20, description="Código (ej: A, B, C)")
    nombre: str = Field(..., min_length=1, max_length=50)
    activo: bool = Field(default=True)


class NivelCreate(NivelBase):
    pass


class NivelUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=20)
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    activo: Optional[bool] = None


class NivelOut(NivelBase):
    id: int
    creado_en: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
