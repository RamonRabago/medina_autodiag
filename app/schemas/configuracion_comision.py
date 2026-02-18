"""Schemas para configuración de comisiones."""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

TIPOS_BASE = ("MANO_OBRA", "PARTES", "SERVICIOS_VENTA", "PRODUCTOS_VENTA")


class ConfiguracionComisionCreate(BaseModel):
    id_usuario: int = Field(..., gt=0)
    tipo_base: str = Field(..., description="MANO_OBRA, PARTES, SERVICIOS_VENTA, PRODUCTOS_VENTA")
    porcentaje: Decimal = Field(..., ge=0, le=100)
    vigencia_desde: date

    @field_validator("tipo_base")
    @classmethod
    def tipo_base_valido(cls, v):
        if v not in TIPOS_BASE:
            raise ValueError(f"tipo_base debe ser uno de: {', '.join(TIPOS_BASE)}")
        return v


class ConfiguracionComisionUpdatePorcentaje(BaseModel):
    porcentaje: Decimal = Field(..., ge=0, le=100)


class ConfiguracionComisionOut(BaseModel):
    id: int
    id_usuario: int
    tipo_base: str
    porcentaje: Decimal
    vigencia_desde: str
    vigencia_hasta: Optional[str] = None
    activo: bool
    empleado_nombre: Optional[str] = None
