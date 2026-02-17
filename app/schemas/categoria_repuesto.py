"""
Schemas de validación para Categoría de Repuestos
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class CategoriaRepuestoBase(BaseModel):
    """Schema base de Categoría de Repuesto"""
    nombre: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Nombre de la categoría"
    )
    descripcion: Optional[str] = Field(
        None,
        max_length=500,
        description="Descripción de la categoría"
    )


class CategoriaRepuestoCreate(CategoriaRepuestoBase):
    """Schema para crear categoría"""
    pass


class CategoriaRepuestoUpdate(BaseModel):
    """Schema para actualizar categoría"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)


class CategoriaRepuestoOut(CategoriaRepuestoBase):
    """Schema de respuesta de Categoría"""
    model_config = ConfigDict(from_attributes=True)
    id_categoria: int
    creado_en: datetime
