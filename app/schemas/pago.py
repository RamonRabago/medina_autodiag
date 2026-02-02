from pydantic import BaseModel
from typing import Optional

class PagoCreate(BaseModel):
    id_venta: int
    metodo: str          # EFECTIVO | TARJETA | TRANSFERENCIA
    monto: float
    referencia: Optional[str] = None