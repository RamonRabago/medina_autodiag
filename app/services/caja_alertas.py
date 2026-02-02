from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.caja_alerta import CajaAlerta


def generar_alerta_diferencia(
    db: Session,
    id_turno: int,
    id_usuario: int,
    diferencia: Decimal
):
    if diferencia == Decimal("0.00"):
        return None

    alerta = CajaAlerta(
        id_turno=id_turno,
        id_usuario=id_usuario,
        tipo="DIFERENCIA_CAJA",
        nivel="CRITICO" if abs(diferencia) >= 50 else "WARNING",
        mensaje=f"Diferencia detectada al cerrar turno: ${diferencia}",
        diferencia=diferencia,
        resuelta=False
    )

    db.add(alerta)  # ⬅️ el commit lo controla el flujo principal
    return alerta

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.caja_alerta import CajaAlerta
from app.models.caja_turno import CajaTurno


def generar_alerta_turno_largo(
    db: Session,
    turno: CajaTurno
):
    if not turno.fecha_apertura:
        return None

    ahora = datetime.utcnow()
    duracion = ahora - turno.fecha_apertura

    # Evitar alertas duplicadas
    alerta_existente = db.query(CajaAlerta).filter(
        CajaAlerta.id_turno == turno.id_turno,
        CajaAlerta.tipo == "TURNO_LARGO",
        CajaAlerta.resuelta == False
    ).first()

    if alerta_existente:
        return None

    if duracion >= timedelta(hours=24):
        nivel = "CRITICO"
    elif duracion >= timedelta(hours=12):
        nivel = "WARNING"
    else:
        return None

    alerta = CajaAlerta(
        id_turno=turno.id_turno,
        id_usuario=turno.id_usuario,
        tipo="TURNO_LARGO",
        nivel=nivel,
        mensaje=f"Turno abierto por más de {int(duracion.total_seconds() // 3600)} horas",
        resuelta=False
    )

    db.add(alerta)
    return alerta