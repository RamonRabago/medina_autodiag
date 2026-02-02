from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.caja_turno import CajaTurno
from app.models.pago import Pago
from app.services.caja_alertas import generar_alerta_diferencia


def cerrar_turno(
    db: Session,
    id_turno: int,
    monto_contado: Decimal
):
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_turno == id_turno,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if not turno:
        raise ValueError("Turno no válido o ya cerrado")

    # 1️⃣ Total esperado (pagos del turno)
    total_pagado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .filter(Pago.id_turno == turno.id_turno)
        .scalar()
    )

    esperado = Decimal(total_pagado)
    diferencia = monto_contado - esperado

    # 2️⃣ Guardar cierre
    turno.monto_cierre = monto_contado
    turno.diferencia = diferencia
    turno.fecha_cierre = func.now()
    turno.estado = "CERRADO"

    # 3️⃣ Generar alerta (si aplica)
    generar_alerta_diferencia(
        db=db,
        id_turno=turno.id_turno,
        id_usuario=turno.id_usuario,
        diferencia=diferencia
    )

    # 4️⃣ Commit único y final
    db.commit()
    db.refresh(turno)

    return turno
