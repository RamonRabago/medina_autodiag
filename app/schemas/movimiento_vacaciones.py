"""Schemas para MovimientoVacaciones (Checador Fase 5)."""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


TipoMovimientoVacacionesStr = Literal["TOMA", "ACREDITACION", "AJUSTE"]


class MovimientoVacacionesBase(BaseModel):
    id_usuario: int = Field(..., description="Empleado")
    fecha: date = Field(..., description="Fecha del movimiento")
    tipo: TipoMovimientoVacacionesStr = Field(..., description="TOMA, ACREDITACION, AJUSTE")
    dias: float = Field(..., description="Días (positivo para TOMA/ACREDITACION; ± para AJUSTE)")
    periodo: Optional[str] = Field(None, max_length=20, description="Ej: 2025 para acreditación anual")
    observaciones: Optional[str] = Field(None, max_length=500)


class MovimientoVacacionesCreate(MovimientoVacacionesBase):
    pass


class MovimientoVacacionesOut(MovimientoVacacionesBase):
    id: int

    class Config:
        from_attributes = True
