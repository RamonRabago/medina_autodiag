"""
Schemas de validación para Movimiento de Inventario
"""
from pydantic import BaseModel, Field, field_validator, field_serializer
from typing import Optional, Any
from datetime import datetime, date
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
    cantidad: Decimal = Field(
        ...,
        ge=0.001,
        description="Cantidad (permite decimales: 37.6 L)"
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
    id_proveedor: Optional[int] = Field(
        None,
        description="ID del proveedor (entradas)"
    )
    imagen_comprobante_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL de imagen de comprobante/factura"
    )
    fecha_adquisicion: Optional[date] = Field(
        None,
        description="Fecha real de adquisición/compra"
    )


class MovimientoInventarioCreate(MovimientoInventarioBase):
    """Schema para crear movimiento de inventario"""
    pass


class MovimientoInventarioOut(MovimientoInventarioBase):
    """Schema de respuesta de Movimiento"""
    id_movimiento: int
    costo_total: Optional[Decimal]
    stock_anterior: Decimal
    stock_nuevo: Decimal
    id_usuario: Optional[int]
    fecha_movimiento: datetime
    creado_en: datetime
    fecha_adquisicion: Optional[date] = None
    
    # Información relacionada (dict o None; acepta ORM con from_attributes)
    repuesto: Optional[Any] = None
    usuario: Optional[Any] = None
    proveedor_nombre: Optional[str] = None

    @field_serializer('repuesto', 'usuario')
    def serializar_orm(self, v: Any):
        """Convierte objetos ORM a dict para JSON"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if hasattr(v, '__table__'):
            return {c.key: getattr(v, c.key) for c in v.__table__.columns}
        return v

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


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
    stock_nuevo: Decimal = Field(..., ge=0, description="Nuevo stock (permite decimales)")
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
