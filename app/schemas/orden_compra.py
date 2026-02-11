"""Schemas para órdenes de compra."""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class DetalleOrdenCompraItem(BaseModel):
    """Ítem de orden: repuesto existente (id_repuesto) o solo nombre (nombre_nuevo)."""
    id_repuesto: Optional[int] = None
    codigo_nuevo: Optional[str] = None
    nombre_nuevo: Optional[str] = None
    cantidad_solicitada: Decimal = Field(..., ge=0.001)
    precio_unitario_estimado: float = Field(0, ge=0)

    @model_validator(mode="after")
    def repuesto_o_nuevo(self):
        has_existing = self.id_repuesto is not None
        has_new = bool((self.nombre_nuevo or "").strip())
        if has_existing and has_new:
            raise ValueError("Usa id_repuesto (existente) o nombre_nuevo (solo nombre), no ambos.")
        if not has_existing and not has_new:
            raise ValueError("Debe indicar id_repuesto (existente) o nombre_nuevo (nombre del repuesto).")
        return self


class ItemsOrdenCompra(BaseModel):
    """Solo items, para agregar a orden existente."""
    items: List[DetalleOrdenCompraItem] = Field(..., min_length=1)


class OrdenCompraCreate(BaseModel):
    id_proveedor: int
    id_catalogo_vehiculo: Optional[int] = None  # Opcional: del catálogo (ordenes de compra)
    observaciones: Optional[str] = None
    comprobante_url: Optional[str] = None
    fecha_estimada_entrega: Optional[str] = None  # YYYY-MM-DD
    items: List[DetalleOrdenCompraItem] = Field(..., min_length=1)


class OrdenCompraUpdate(BaseModel):
    id_proveedor: Optional[int] = None  # Solo editable en BORRADOR
    observaciones: Optional[str] = None
    referencia_proveedor: Optional[str] = None
    comprobante_url: Optional[str] = None
    fecha_estimada_entrega: Optional[str] = None  # YYYY-MM-DD
    id_catalogo_vehiculo: Optional[int] = None


class ItemRecepcion(BaseModel):
    id_detalle: int
    cantidad_recibida: Decimal = Field(..., ge=0)
    precio_unitario_real: Optional[float] = Field(None, ge=0)


class RecepcionMercanciaRequest(BaseModel):
    items: List[ItemRecepcion] = Field(..., min_length=1)
    referencia_proveedor: Optional[str] = None


class PagoOrdenCompraCreate(BaseModel):
    monto: float = Field(..., gt=0)
    metodo: str = Field(..., pattern="^(EFECTIVO|TARJETA|TRANSFERENCIA|CHEQUE)$")
    referencia: Optional[str] = None
    observaciones: Optional[str] = None
