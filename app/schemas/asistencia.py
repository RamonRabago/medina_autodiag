"""Schemas para Asistencia (Checador Fase 3)."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import date


TipoAsistenciaStr = Literal[
    "TRABAJO", "FESTIVO", "VACACION",
    "PERMISO_CON_GOCE", "PERMISO_SIN_GOCE",
    "INCAPACIDAD", "FALTA"
]


class AsistenciaBase(BaseModel):
    id_usuario: int = Field(..., description="Empleado")
    fecha: date = Field(..., description="Día específico")
    tipo: TipoAsistenciaStr = Field(..., description="TRABAJO, FESTIVO, VACACION, etc.")
    horas_trabajadas: Optional[float] = Field(None, ge=0, le=24)
    turno_completo: Optional[bool] = Field(True)
    aplica_bono_puntualidad: Optional[bool] = Field(True)
    observaciones: Optional[str] = Field(None, max_length=500)
    id_referencia: Optional[int] = Field(None)


class AsistenciaCreate(AsistenciaBase):
    pass


class AsistenciaUpdate(BaseModel):
    tipo: Optional[TipoAsistenciaStr] = Field(None)
    horas_trabajadas: Optional[float] = Field(None, ge=0, le=24)
    turno_completo: Optional[bool] = None
    aplica_bono_puntualidad: Optional[bool] = None
    observaciones: Optional[str] = Field(None, max_length=500)
    id_referencia: Optional[int] = None


class AsistenciaOut(AsistenciaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
