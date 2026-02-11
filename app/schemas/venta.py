from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal

class DetalleVentaCreate(BaseModel):
    tipo: str           # PRODUCTO | SERVICIO
    id_item: int
    descripcion: str
    cantidad: Decimal = Field(default=1, ge=0.001)  # Permite decimales (ej: 2.5 L de aceite)
    precio_unitario: float

class VentaCreate(BaseModel):
    id_cliente: Optional[int] = None
    id_vehiculo: Optional[int] = None
    requiere_factura: bool = False
    comentarios: Optional[str] = None
    detalles: List[DetalleVentaCreate]


class VentaUpdate(BaseModel):
    id_cliente: Optional[int] = None
    id_vehiculo: Optional[int] = None
    requiere_factura: bool = False
    comentarios: Optional[str] = None
    detalles: List[DetalleVentaCreate]
