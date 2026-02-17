"""
Schemas de validación para Proveedor
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

from app.utils.validators import validar_telefono_mexico, validar_email_opcional


class ProveedorBase(BaseModel):
    """Schema base de Proveedor"""
    nombre: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Nombre del proveedor"
    )
    contacto: Optional[str] = Field(
        None,
        max_length=100,
        description="Nombre de la persona de contacto"
    )
    telefono: Optional[str] = Field(
        None,
        description="Teléfono a 10 dígitos"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email del proveedor"
    )
    direccion: Optional[str] = Field(
        None,
        max_length=500,
        description="Dirección del proveedor"
    )
    rfc: Optional[str] = Field(
        None,
        min_length=12,
        max_length=13,
        description="RFC del proveedor"
    )
    activo: bool = Field(
        default=True,
        description="Estado del proveedor"
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
    
    @field_validator('rfc')
    @classmethod
    def validar_rfc(cls, v: Optional[str]) -> Optional[str]:
        """Valida y normaliza RFC"""
        if v:
            v = v.strip().upper()
            if len(v) not in [12, 13]:
                raise ValueError("RFC debe tener 12 o 13 caracteres")
            return v
        return v


class ProveedorCreate(ProveedorBase):
    """Schema para crear proveedor"""
    pass


class ProveedorUpdate(BaseModel):
    """Schema para actualizar proveedor"""
    nombre: Optional[str] = Field(None, min_length=3, max_length=150)
    contacto: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    direccion: Optional[str] = Field(None, max_length=500)
    rfc: Optional[str] = Field(None, min_length=12, max_length=13)
    activo: Optional[bool] = None
    
    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validar_telefono_mexico(v)
        return v
    
    @field_validator('rfc')
    @classmethod
    def validar_rfc(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if len(v) not in [12, 13]:
                raise ValueError("RFC debe tener 12 o 13 caracteres")
            return v
        return v


class ProveedorOut(ProveedorBase):
    """Schema de respuesta de Proveedor"""
    model_config = ConfigDict(from_attributes=True)
    id_proveedor: int
    creado_en: datetime
