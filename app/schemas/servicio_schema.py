# app/schemas/servicio.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal

class ServicioBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50, description="Código único del servicio")
    nombre: str = Field(..., min_length=3, max_length=200, description="Nombre del servicio")
    descripcion: Optional[str] = Field(None, description="Descripción detallada del servicio")
    categoria: str = Field(..., description="Categoría del servicio")
    precio_base: Decimal = Field(..., ge=0, decimal_places=2, description="Precio base del servicio")
    tiempo_estimado_minutos: int = Field(..., ge=1, description="Tiempo estimado en minutos")
    activo: bool = Field(default=True, description="Si el servicio está activo")
    requiere_repuestos: bool = Field(default=False, description="Si típicamente requiere repuestos")

    @field_validator('categoria')
    @classmethod
    def validar_categoria(cls, v):
        categorias_validas = [
            "MANTENIMIENTO", "REPARACION", "DIAGNOSTICO", "ELECTRICIDAD",
            "SUSPENSION", "FRENOS", "MOTOR", "TRANSMISION", 
            "AIRE_ACONDICIONADO", "CARROCERIA", "OTROS"
        ]
        if v not in categorias_validas:
            raise ValueError(f"Categoría debe ser una de: {', '.join(categorias_validas)}")
        return v

class ServicioCreate(ServicioBase):
    """Schema para crear un nuevo servicio"""
    pass

class ServicioUpdate(BaseModel):
    """Schema para actualizar un servicio (todos los campos opcionales)"""
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    precio_base: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    tiempo_estimado_minutos: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None
    requiere_repuestos: Optional[bool] = None

    @field_validator('categoria')
    @classmethod
    def validar_categoria(cls, v):
        if v is None:
            return v
        categorias_validas = [
            "MANTENIMIENTO", "REPARACION", "DIAGNOSTICO", "ELECTRICIDAD",
            "SUSPENSION", "FRENOS", "MOTOR", "TRANSMISION", 
            "AIRE_ACONDICIONADO", "CARROCERIA", "OTROS"
        ]
        if v not in categorias_validas:
            raise ValueError(f"Categoría debe ser una de: {', '.join(categorias_validas)}")
        return v

class ServicioResponse(ServicioBase):
    """Schema para respuesta con datos del servicio"""
    id: int

    class Config:
        from_attributes = True

class ServicioListResponse(BaseModel):
    """Schema para listado de servicios"""
    servicios: list[ServicioResponse]
    total: int
    pagina: int
    total_paginas: int

    class Config:
        from_attributes = True
