# app/schemas/servicio_schema.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from decimal import Decimal


class ServicioBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50, description="Código único del servicio")
    nombre: str = Field(..., min_length=3, max_length=200, description="Nombre del servicio")
    descripcion: Optional[str] = Field(None, description="Descripción detallada del servicio")
    id_categoria: int = Field(..., description="ID de la categoría del servicio")
    precio_base: Decimal = Field(..., ge=0, decimal_places=2, description="Precio base del servicio")
    tiempo_estimado_minutos: int = Field(..., ge=1, description="Tiempo estimado en minutos")
    activo: bool = Field(default=True, description="Si el servicio está activo")
    requiere_repuestos: bool = Field(default=False, description="Si típicamente requiere repuestos")


class ServicioCreate(ServicioBase):
    pass


class ServicioUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = None
    id_categoria: Optional[int] = None
    precio_base: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    tiempo_estimado_minutos: Optional[int] = Field(None, ge=1)
    activo: Optional[bool] = None
    requiere_repuestos: Optional[bool] = None


class ServicioResponse(ServicioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    categoria_nombre: str = ""


class ServicioListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    servicios: list[ServicioResponse]
    total: int
    pagina: int
    total_paginas: int
