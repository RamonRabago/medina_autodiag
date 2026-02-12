from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from typing import Literal
from decimal import Decimal

PeriodoPago = Literal["SEMANAL", "QUINCENAL", "MENSUAL"]


class UsuarioBase(BaseModel):
    nombre: str
    email: Optional[EmailStr] = None
    rol: Literal["ADMIN", "EMPLEADO", "TECNICO", "CAJA"] = "TECNICO"
    activo: bool = True
    salario_base: Optional[Decimal] = Field(None, ge=0, description="Salario base del empleado (nómina)")
    periodo_pago: Optional[PeriodoPago] = Field(None, description="Periodo de pago: semanal, quincenal, mensual")
    bono_puntualidad: Optional[Decimal] = Field(None, ge=0, description="Bono por puntualidad (se suma cuando cumple)")


class UsuarioCreate(UsuarioBase):
    password: str = Field(
        ...,
        min_length=4,
        max_length=72,
        description="Contraseña (máx 72 caracteres)"
    )


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = None
    salario_base: Optional[Decimal] = Field(None, ge=0)
    periodo_pago: Optional[PeriodoPago] = None
    bono_puntualidad: Optional[Decimal] = Field(None, ge=0)


class UsuarioOut(UsuarioBase):
    id_usuario: int

    class Config:
        from_attributes = True
