"""
Schemas de validación para Cliente
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

from app.utils.validators import validar_telefono_mexico, validar_email_opcional


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
    email: Optional[EmailStr] = Field(
        None,
        description="Email del cliente"
    )
    direccion: Optional[str] = Field(
        None,
        max_length=500,
        description="Dirección completa"
    )
    
    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato de teléfono mexicano"""
        if v:
            return validar_telefono_mexico(v)
        return v
    
    @field_validator('email')
    @classmethod
    def validar_email(cls, v: Optional[str]) -> Optional[str]:
        """Normaliza email a minúsculas"""
        return validar_email_opcional(v)
    
    @field_validator('nombre')
    @classmethod
    def limpiar_nombre(cls, v: str) -> str:
        """Limpia y capitaliza nombre"""
        return v.strip().title()


class ClienteCreate(ClienteBase):
    """Schema para crear cliente"""
    pass


class ClienteUpdate(BaseModel):
    """Schema para actualizar cliente"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=120)
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = Field(None, max_length=500)
    
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


class ClienteOut(ClienteBase):
    """Schema de respuesta de Cliente"""
    id_cliente: int
    creado_en: datetime
    
    class Config:
        from_attributes = True
