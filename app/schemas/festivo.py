"""Schemas para Festivos (Checador Fase 2)."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date


class FestivoBase(BaseModel):
    fecha: date = Field(..., description="Fecha del festivo")
    nombre: str = Field(..., min_length=1, max_length=100, description="Ej: Navidad")
    anio: int = Field(..., ge=2000, le=2100, description="Año para filtrar")


class FestivoCreate(FestivoBase):
    pass


class FestivoUpdate(BaseModel):
    fecha: Optional[date] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    anio: Optional[int] = Field(None, ge=2000, le=2100)


class FestivoOut(FestivoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
