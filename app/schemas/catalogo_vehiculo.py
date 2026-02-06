"""Schemas para catálogo de vehículos (ordenes de compra, futura compatibilidad con partes)."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class CatalogoVehiculoCreate(BaseModel):
    """Crear entrada en catálogo. Año, Marca, Modelo obligatorios. Versión y Motor opcionales."""
    anio: int = Field(..., ge=1900, le=2030, description="Año")
    marca: str = Field(..., min_length=2, max_length=80, description="Marca")
    modelo: str = Field(..., min_length=1, max_length=80, description="Modelo")
    version_trim: Optional[str] = Field(None, max_length=100, description="Versión / nivel de equipamiento")
    motor: Optional[str] = Field(None, max_length=80, description="Motor")
    vin: Optional[str] = Field(None, max_length=50, description="Número de serie (VIN)")

    @field_validator('marca', 'modelo', 'version_trim')
    @classmethod
    def capitalizar(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().title() if v and v.strip() else None

    @field_validator('vin')
    @classmethod
    def mayusculas(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v and v.strip() else None


class CatalogoVehiculoOut(BaseModel):
    """Respuesta del catálogo."""
    id: int
    anio: int
    marca: str
    modelo: str
    version_trim: Optional[str] = None
    motor: Optional[str] = None
    vin: Optional[str] = None
    creado_en: Optional[datetime] = None

    class Config:
        from_attributes = True
