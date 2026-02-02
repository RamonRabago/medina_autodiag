from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class TurnoAbrir(BaseModel):
    monto_apertura: Decimal

class TurnoCerrar(BaseModel):
    monto_cierre: Decimal

class TurnoOut(BaseModel):
    id_turno: int
    id_usuario: int
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    monto_apertura: Decimal
    monto_cierre: Decimal | None
    estado: str

    class Config:
        from_attributes = True
