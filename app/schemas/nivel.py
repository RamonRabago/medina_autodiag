"""Schemas para Nivel"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


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

    class Config:
        from_attributes = True
