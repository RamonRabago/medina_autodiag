"""
Schemas de validación para Vehículo
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime


class VehiculoBase(BaseModel):
    """Schema base de Vehículo (color y motor opcionales y separados)."""
    marca: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Marca del vehículo"
    )
    modelo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Modelo del vehículo"
    )
    anio: int = Field(
        ...,
        ge=1900,
        le=2030,
        description="Año del vehículo"
    )
    color: Optional[str] = Field(
        None,
        max_length=30,
        description="Color del vehículo"
    )
    numero_serie: Optional[str] = Field(
        None,
        max_length=50,
        description="Número de serie (VIN)"
    )
    motor: Optional[str] = Field(None, max_length=50, description="Motor/desplazamiento (ej. 1.8)")
    id_cliente: int = Field(
        ...,
        gt=0,
        description="ID del cliente propietario"
    )

    @field_validator('marca', 'modelo')
    @classmethod
    def capitalizar(cls, v: str) -> str:
        """Capitaliza marca y modelo"""
        return v.strip().title()
    
    @field_validator('color')
    @classmethod
    def capitalizar_color(cls, v: Optional[str]) -> Optional[str]:
        """Capitaliza color si existe"""
        if v:
            return v.strip().title()
        return v
    
    @field_validator('numero_serie')
    @classmethod
    def limpiar_serie(cls, v: Optional[str]) -> Optional[str]:
        """Convierte número de serie a mayúsculas"""
        if v:
            return v.strip().upper()
        return v


class VehiculoCreate(VehiculoBase):
    """Schema para crear vehículo"""
    pass


class VehiculoCreateSinCliente(BaseModel):
    """Schema para crear vehículo sin asociar a cliente (ej. órdenes de compra). Sin color."""
    marca: str = Field(..., min_length=2, max_length=50)
    modelo: str = Field(..., min_length=1, max_length=50)
    anio: int = Field(..., ge=1900, le=2030)
    motor: Optional[str] = Field(None, max_length=50)
    numero_serie: Optional[str] = Field(None, max_length=50)

    @field_validator('marca', 'modelo')
    @classmethod
    def capitalizar(cls, v: str) -> str:
        return v.strip().title() if v else v

    @field_validator('numero_serie')
    @classmethod
    def limpiar_serie(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v and v.strip() else None


class VehiculoUpdate(BaseModel):
    """Schema para actualizar vehículo (color y motor separados)."""
    marca: Optional[str] = Field(None, min_length=2, max_length=50)
    modelo: Optional[str] = Field(None, min_length=1, max_length=50)
    anio: Optional[int] = Field(None, ge=1900, le=2030)
    color: Optional[str] = Field(None, max_length=30)
    numero_serie: Optional[str] = Field(None, max_length=50)
    motor: Optional[str] = Field(None, max_length=50, description="Motor/desplazamiento (ej. 1.8)")
    id_cliente: Optional[int] = Field(None, gt=0)

    @field_validator('marca', 'modelo')
    @classmethod
    def capitalizar(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().title()
        return v


class VehiculoOut(BaseModel):
    """Schema de respuesta de Vehículo (color, numero_serie/VIN, motor separados)."""
    id_vehiculo: int
    marca: str
    modelo: str
    anio: int
    color: Optional[str] = None
    numero_serie: Optional[str] = None
    motor: Optional[str] = None
    id_cliente: Optional[int] = None  # None para vehículos sin asociar a cliente
    cliente_nombre: Optional[str] = None
    creado_en: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
