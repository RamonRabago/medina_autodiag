from pydantic import BaseModel
from typing import List, Optional

class DetalleVentaCreate(BaseModel):
    tipo: str           # PRODUCTO | SERVICIO
    id_item: int
    descripcion: str
    cantidad: int = 1
    precio_unitario: float

class VentaCreate(BaseModel):
    id_cliente: Optional[int] = None
    id_vehiculo: Optional[int] = None
    detalles: List[DetalleVentaCreate]
