from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TurnoAbrir(BaseModel):
    monto_apertura: Decimal


class TurnoCerrar(BaseModel):
    monto_cierre: Decimal


class TurnoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_turno: int
    id_usuario: int
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    monto_apertura: Decimal
    monto_cierre: Decimal | None
    estado: str
