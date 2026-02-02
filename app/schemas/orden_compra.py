"""Schemas para órdenes de compra."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class DetalleOrdenCompraItem(BaseModel):
    id_repuesto: int
    cantidad_solicitada: int = Field(..., ge=1)
    precio_unitario_estimado: float = Field(..., ge=0)


class ItemsOrdenCompra(BaseModel):
    """Solo items, para agregar a orden existente."""
    items: List[DetalleOrdenCompraItem] = Field(..., min_length=1)


class OrdenCompraCreate(BaseModel):
    id_proveedor: int
    observaciones: Optional[str] = None
    items: List[DetalleOrdenCompraItem] = Field(..., min_length=1)


class OrdenCompraUpdate(BaseModel):
    observaciones: Optional[str] = None
    referencia_proveedor: Optional[str] = None


class ItemRecepcion(BaseModel):
    id_detalle: int
    cantidad_recibida: int = Field(..., ge=0)
    precio_unitario_real: Optional[float] = Field(None, ge=0)


class RecepcionMercanciaRequest(BaseModel):
    items: List[ItemRecepcion] = Field(..., min_length=1)
    referencia_proveedor: Optional[str] = None
