"""Schemas para cuentas por pagar manuales."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class CuentaPagarManualCreate(BaseModel):
    id_proveedor: Optional[int] = None
    acreedor_nombre: Optional[str] = Field(None, max_length=150)
    referencia_factura: Optional[str] = Field(None, max_length=80)
    concepto: str = Field(..., min_length=1, max_length=200)
    monto_total: float = Field(..., gt=0)
    fecha_registro: Optional[str] = None  # YYYY-MM-DD, default hoy
    fecha_vencimiento: Optional[str] = None  # YYYY-MM-DD
    observaciones: Optional[str] = None


class CuentaPagarManualUpdate(BaseModel):
    referencia_factura: Optional[str] = Field(None, max_length=80)
    concepto: Optional[str] = Field(None, min_length=1, max_length=200)
    monto_total: Optional[float] = Field(None, gt=0)
    fecha_vencimiento: Optional[str] = None
    observaciones: Optional[str] = None


class PagoCuentaPagarManualCreate(BaseModel):
    monto: float = Field(..., gt=0)
    metodo: str = Field(..., pattern="^(EFECTIVO|TARJETA|TRANSFERENCIA|CHEQUE)$")
    referencia: Optional[str] = None
    observaciones: Optional[str] = None
