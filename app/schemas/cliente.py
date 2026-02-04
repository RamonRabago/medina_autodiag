"""
Schemas de validación para Cliente
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

from app.utils.validators import validar_telefono_mexico, validar_email_opcional, validar_rfc_opcional


class ClienteBase(BaseModel):
    """Schema base de Cliente"""
    nombre: str = Field(
        ..., 
        min_length=3, 
        max_length=120,
        description="Nombre completo del cliente"
    )
    telefono: Optional[str] = Field(
        None,
        description="Teléfono a 10 dígitos"
    )
    email: Optional[str] = Field(
        None,
        max_length=100,
        description="Email del cliente (opcional)"
    )
    direccion: Optional[str] = Field(
        None,
        max_length=500,
        description="Dirección (opcional)"
    )
    rfc: Optional[str] = Field(
        None,
        max_length=13,
        description="RFC mexicano (12 o 13 caracteres, opcional)"
    )

    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato de teléfono mexicano"""
        if v:
            return validar_telefono_mexico(v)
        return v
    
    @field_validator('email', mode='before')
    @classmethod
    def validar_email(cls, v: Optional[str]) -> Optional[str]:
        """Convierte vacío a None y valida formato si se proporciona"""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return validar_email_opcional(v)
    
    @field_validator('nombre')
    @classmethod
    def limpiar_nombre(cls, v: str) -> str:
        """Limpia y capitaliza nombre"""
        return v.strip().title()

    @field_validator('rfc', mode='before')
    @classmethod
    def validar_rfc(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato RFC mexicano (opcional). Convierte vacío a None."""
        return validar_rfc_opcional(v)


class ClienteCreate(ClienteBase):
    """Schema para crear cliente"""
    pass


class ClienteUpdate(BaseModel):
    """Schema para actualizar cliente"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=120)
    telefono: Optional[str] = None
    email: Optional[str] = Field(None, max_length=100)
    direccion: Optional[str] = Field(None, max_length=500)
    rfc: Optional[str] = Field(None, max_length=13)

    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validar_telefono_mexico(v)
        return v
    
    @field_validator('nombre')
    @classmethod
    def limpiar_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().title()
        return v

    @field_validator('rfc', mode='before')
    @classmethod
    def validar_rfc(cls, v: Optional[str]) -> Optional[str]:
        return validar_rfc_opcional(v)

    @field_validator('email', mode='before')
    @classmethod
    def validar_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return validar_email_opcional(v)


class ClienteOut(ClienteBase):
    """Schema de respuesta de Cliente"""
    id_cliente: int
    creado_en: datetime
    
    class Config:
        from_attributes = True
