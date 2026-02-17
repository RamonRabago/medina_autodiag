"""Schemas para Fila"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class FilaBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=20, description="Código (ej: 1, 2, 3)")
    nombre: str = Field(..., min_length=1, max_length=50)
    activo: bool = Field(default=True)


class FilaCreate(FilaBase):
    pass


class FilaUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=20)
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    activo: Optional[bool] = None


class FilaOut(FilaBase):
    id: int
    creado_en: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
