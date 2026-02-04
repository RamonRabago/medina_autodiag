"""
Schemas de validación para Repuesto
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class RepuestoBase(BaseModel):
    """Schema base de Repuesto"""
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código único del repuesto"
    )
    nombre: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Nombre del repuesto"
    )
    descripcion: Optional[str] = Field(
        None,
        max_length=1000,
        description="Descripción detallada"
    )
    id_categoria: Optional[int] = Field(
        None,
        description="ID de la categoría"
    )
    id_proveedor: Optional[int] = Field(
        None,
        description="ID del proveedor principal"
    )
    stock_minimo: int = Field(
        default=5,
        ge=0,
        description="Stock mínimo requerido"
    )
    stock_maximo: int = Field(
        default=100,
        ge=1,
        description="Stock máximo permitido"
    )
    ubicacion: Optional[str] = Field(
        None,
        max_length=50,
        description="Ubicación física en bodega"
    )
    imagen_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL de la foto del producto"
    )
    precio_compra: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Precio de compra unitario"
    )
    precio_venta: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Precio de venta al público"
    )
    marca: Optional[str] = Field(
        None,
        max_length=100,
        description="Marca del repuesto"
    )
    modelo_compatible: Optional[str] = Field(
        None,
        max_length=200,
        description="Modelos de vehículos compatibles"
    )
    unidad_medida: str = Field(
        default="PZA",
        max_length=20,
        description="Unidad de medida (PZA, LT, KG, etc.)"
    )
    activo: bool = Field(
        default=True,
        description="Estado del repuesto"
    )
    
    @field_validator('codigo')
    @classmethod
    def normalizar_codigo(cls, v: str) -> str:
        """Normaliza el código a mayúsculas y sin espacios"""
        return v.strip().upper()
    
    @field_validator('precio_venta')
    @classmethod
    def validar_precio_venta(cls, v: Decimal, info) -> Decimal:
        """Valida que el precio de venta sea mayor al de compra"""
        if 'precio_compra' in info.data and v < info.data['precio_compra']:
            raise ValueError("El precio de venta debe ser mayor o igual al precio de compra")
        return v
    
    @field_validator('stock_maximo')
    @classmethod
    def validar_stock_maximo(cls, v: int, info) -> int:
        """Valida que el stock máximo sea mayor al mínimo"""
        if 'stock_minimo' in info.data and v < info.data['stock_minimo']:
            raise ValueError("El stock máximo debe ser mayor al stock mínimo")
        return v
    
    @field_validator('unidad_medida')
    @classmethod
    def normalizar_unidad(cls, v: str) -> str:
        """Normaliza la unidad de medida a mayúsculas"""
        return v.strip().upper()


class RepuestoCreate(RepuestoBase):
    """Schema para crear repuesto"""
    stock_actual: int = Field(
        default=0,
        ge=0,
        description="Stock inicial"
    )


class RepuestoUpdate(BaseModel):
    """Schema para actualizar repuesto"""
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    nombre: Optional[str] = Field(None, min_length=3, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    id_categoria: Optional[int] = None
    id_proveedor: Optional[int] = None
    stock_minimo: Optional[int] = Field(None, ge=0)
    stock_maximo: Optional[int] = Field(None, ge=1)
    ubicacion: Optional[str] = Field(None, max_length=50)
    imagen_url: Optional[str] = Field(None, max_length=500)
    precio_compra: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    precio_venta: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    marca: Optional[str] = Field(None, max_length=100)
    modelo_compatible: Optional[str] = Field(None, max_length=200)
    unidad_medida: Optional[str] = Field(None, max_length=20)
    activo: Optional[bool] = None
    
    @field_validator('codigo')
    @classmethod
    def normalizar_codigo(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().upper()
        return v


class RepuestoOut(BaseModel):
    """Schema de respuesta de Repuesto"""
    id_repuesto: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    id_categoria: Optional[int] = None
    id_proveedor: Optional[int] = None
    stock_actual: int
    stock_minimo: int
    stock_maximo: int
    ubicacion: Optional[str] = None
    imagen_url: Optional[str] = None
    precio_compra: Decimal
    precio_venta: Decimal
    marca: Optional[str] = None
    modelo_compatible: Optional[str] = None
    unidad_medida: str = "PZA"
    activo: bool = True
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None
    categoria_nombre: str = ""
    proveedor_nombre: str = ""
    eliminado: bool = False
    fecha_eliminacion: Optional[datetime] = None
    motivo_eliminacion: Optional[str] = None

    class Config:
        from_attributes = True


class RepuestoConStock(RepuestoOut):
    """Schema de repuesto con información adicional de stock"""
    necesita_reorden: bool = Field(
        description="Indica si el stock está por debajo del mínimo"
    )
    dias_sin_movimiento: Optional[int] = Field(
        None,
        description="Días desde el último movimiento"
    )
    valor_inventario: Decimal = Field(
        description="Valor total del inventario (stock_actual * precio_compra)"
    )
