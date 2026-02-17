"""
Schemas para Gastos Operativos.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal

CategoriaGasto = Literal["RENTA", "SERVICIOS", "MATERIAL", "NOMINA", "OTROS", "DEVOLUCION_VENTA"]


class GastoOperativoBase(BaseModel):
    fecha: date
    concepto: str = Field(..., min_length=1, max_length=200)
    monto: Decimal = Field(..., ge=0.01)
    categoria: str = Field(default="OTROS", pattern="^(RENTA|SERVICIOS|MATERIAL|NOMINA|OTROS|DEVOLUCION_VENTA)$")
    observaciones: Optional[str] = None


class GastoOperativoCreate(GastoOperativoBase):
    id_turno: Optional[int] = None


class GastoOperativoUpdate(BaseModel):
    fecha: Optional[date] = None
    concepto: Optional[str] = Field(None, min_length=1, max_length=200)
    monto: Optional[Decimal] = Field(None, ge=0.01)
    categoria: Optional[CategoriaGasto] = None
    observaciones: Optional[str] = None


class GastoOperativoOut(BaseModel):
    id_gasto: int
    fecha: date
    concepto: str
    monto: Decimal
    categoria: str
    id_turno: Optional[int]
    id_usuario: int
    observaciones: Optional[str]
    creado_en: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
