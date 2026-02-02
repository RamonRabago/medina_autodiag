"""
Schemas de validación para Movimiento de Inventario
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.movimiento_inventario import TipoMovimiento


class MovimientoInventarioBase(BaseModel):
    """Schema base de Movimiento de Inventario"""
    id_repuesto: int = Field(
        ...,
        description="ID del repuesto"
    )
    tipo_movimiento: TipoMovimiento = Field(
        ...,
        description="Tipo de movimiento (ENTRADA, SALIDA, etc.)"
    )
    cantidad: int = Field(
        ...,
        ge=1,
        description="Cantidad de unidades del movimiento"
    )
    precio_unitario: Optional[Decimal] = Field(
        None,
        ge=0,
        decimal_places=2,
        description="Precio unitario del movimiento"
    )
    referencia: Optional[str] = Field(
        None,
        max_length=100,
        description="Referencia (factura, orden, etc.)"
    )
    motivo: Optional[str] = Field(
        None,
        max_length=500,
        description="Motivo o descripción del movimiento"
    )
    id_venta: Optional[int] = Field(
        None,
        description="ID de venta asociada (si aplica)"
    )


class MovimientoInventarioCreate(MovimientoInventarioBase):
    """Schema para crear movimiento de inventario"""
    pass


class MovimientoInventarioOut(MovimientoInventarioBase):
    """Schema de respuesta de Movimiento"""
    id_movimiento: int
    costo_total: Optional[Decimal]
    stock_anterior: int
    stock_nuevo: int
    id_usuario: Optional[int]
    fecha_movimiento: datetime
    creado_en: datetime
    
    # Información relacionada
    repuesto: Optional[dict] = None
    usuario: Optional[dict] = None
    
    class Config:
        from_attributes = True


class MovimientoInventarioFiltros(BaseModel):
    """Schema para filtros de búsqueda de movimientos"""
    id_repuesto: Optional[int] = None
    tipo_movimiento: Optional[TipoMovimiento] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    id_usuario: Optional[int] = None
    referencia: Optional[str] = None


class AjusteInventario(BaseModel):
    """Schema para ajuste manual de inventario"""
    id_repuesto: int = Field(..., description="ID del repuesto")
    stock_nuevo: int = Field(..., ge=0, description="Nuevo stock a establecer")
    motivo: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Motivo del ajuste (mínimo 10 caracteres)"
    )
    referencia: Optional[str] = Field(
        None,
        max_length=100,
        description="Referencia del ajuste"
    )
