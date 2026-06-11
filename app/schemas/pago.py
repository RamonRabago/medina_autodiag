from typing import Optional

from pydantic import BaseModel


class PagoCreate(BaseModel):
    id_venta: int
    metodo: str  # EFECTIVO | TARJETA | TRANSFERENCIA
    monto: float
    referencia: Optional[str] = None
