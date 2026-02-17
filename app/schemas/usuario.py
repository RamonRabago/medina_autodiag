from pydantic import BaseModel, ConfigDict, EmailStr, Field
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
    # Checador (Etapa 2): config flexible por empleado
    horas_por_dia: Optional[Decimal] = Field(None, ge=0, le=24, description="Horas por día laboral")
    dias_por_semana: Optional[int] = Field(None, ge=1, le=7, description="Días laborales por semana")
    dias_vacaciones_saldo: Optional[Decimal] = Field(None, ge=0, description="Saldo de días de vacaciones")
    horario_inicio: Optional[str] = Field(None, description="Hora inicio (HH:MM)")
    horario_fin: Optional[str] = Field(None, description="Hora fin (HH:MM)")
    dias_semana_trabaja: Optional[str] = Field(None, description="Días que trabaja: 1=lun..7=dom, ej. 1,2,3,4,5")
    checa_entrada_salida: Optional[bool] = Field(True, description="True=usa reloj checador; False=registro manual por Admin")


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
    horas_por_dia: Optional[Decimal] = Field(None, ge=0, le=24)
    dias_por_semana: Optional[int] = Field(None, ge=1, le=7)
    dias_vacaciones_saldo: Optional[Decimal] = Field(None, ge=0)
    horario_inicio: Optional[str] = None
    horario_fin: Optional[str] = None
    dias_semana_trabaja: Optional[str] = None
    checa_entrada_salida: Optional[bool] = None


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id_usuario: int
