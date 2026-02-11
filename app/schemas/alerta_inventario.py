"""
Schemas de validación para Alerta de Inventario
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.alerta_inventario import TipoAlertaInventario


class AlertaInventarioBase(BaseModel):
    """Schema base de Alerta de Inventario"""
    tipo_alerta: TipoAlertaInventario
    mensaje: str
    stock_actual: Optional[Decimal] = None
    stock_minimo: Optional[Decimal] = None
    stock_maximo: Optional[Decimal] = None


class AlertaInventarioCreate(AlertaInventarioBase):
    """Schema para crear alerta"""
    id_repuesto: int


class AlertaInventarioOut(AlertaInventarioBase):
    """Schema de respuesta de Alerta"""
    id_alerta: int
    id_repuesto: int
    activa: bool
    fecha_creacion: datetime
    fecha_resolucion: Optional[datetime]
    resuelto_por: Optional[int]
    
    # Información relacionada
    repuesto: Optional[dict] = None
    
    class Config:
        from_attributes = True


class AlertaInventarioResolver(BaseModel):
    """Schema para resolver una alerta"""
    id_alerta: int = Field(..., description="ID de la alerta a resolver")


class ResumenAlertas(BaseModel):
    """Schema para resumen de alertas"""
    total_alertas: int
    alertas_criticas: int
    alertas_stock_bajo: int
    alertas_sin_stock: int
    alertas_sin_movimiento: int
    alertas_sobre_stock: int
