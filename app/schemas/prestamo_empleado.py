"""
Schemas para préstamos a empleados.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date
from decimal import Decimal

PeriodoDescuento = str  # "SEMANAL" | "QUINCENAL" | "MENSUAL"
EstadoPrestamo = str  # "ACTIVO" | "LIQUIDADO" | "CANCELADO"


class PrestamoEmpleadoBase(BaseModel):
    id_usuario: int
    monto_total: Decimal = Field(..., ge=0.01)
    descuento_por_periodo: Decimal = Field(..., ge=0.01)
    periodo_descuento: str = Field(..., pattern="^(SEMANAL|QUINCENAL|MENSUAL)$")
    fecha_inicio: date
    observaciones: Optional[str] = None


class PrestamoEmpleadoCreate(PrestamoEmpleadoBase):
    pass


class PrestamoEmpleadoUpdate(BaseModel):
    estado: Optional[str] = Field(None, pattern="^(ACTIVO|LIQUIDADO|CANCELADO)$")
    observaciones: Optional[str] = None


class DescuentoPrestamoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    monto_descontado: Decimal
    fecha_periodo: date


class PrestamoEmpleadoOut(BaseModel):
    id: int
    id_usuario: int
    monto_total: Decimal
    descuento_por_periodo: Decimal
    periodo_descuento: str
    fecha_inicio: date
    estado: str
    observaciones: Optional[str] = None
    saldo_pendiente: Optional[Decimal] = None  # calculado
    empleado_nombre: Optional[str] = None  # para listados admin
    model_config = ConfigDict(from_attributes=True)


class PrestamoEmpleadoConDescuentosOut(PrestamoEmpleadoOut):
    descuentos: list = []


class AplicarDescuentoIn(BaseModel):
    monto: Decimal = Field(..., ge=0.01)
    fecha_periodo: date = Field(..., description="Primer día del periodo (ej. lunes si es semanal)")
