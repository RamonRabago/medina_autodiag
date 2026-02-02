from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from typing import Literal

class UsuarioBase(BaseModel):
    nombre: str
    email: Optional[EmailStr] = None
    #rol: str = "TECNICO"
    rol: Literal["ADMIN", "EMPLEADO", "TECNICO", "CAJA"] = "TECNICO"
    activo: bool = True

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

class UsuarioOut(UsuarioBase):
    id_usuario: int

    class Config:
        from_attributes = True
