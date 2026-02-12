from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.caja_turno import CajaTurno
from app.models.pago import Pago
from app.models.pago_orden_compra import PagoOrdenCompra
from app.models.cuenta_pagar_manual import PagoCuentaPagarManual
from app.models.gasto_operativo import GastoOperativo
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

    # 1️⃣ Total esperado: apertura + cobros EFECTIVO - egresos (pagos OC + pagos cuentas manuales + gastos)
    # Solo cobros en efectivo: el cierre es por efectivo físico en caja
    total_efectivo_cobrado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .filter(Pago.id_turno == turno.id_turno, Pago.metodo == "EFECTIVO")
        .scalar()
    )
    total_pagos_oc_efectivo = (
        db.query(func.coalesce(func.sum(PagoOrdenCompra.monto), 0))
        .filter(
            PagoOrdenCompra.id_turno == turno.id_turno,
            PagoOrdenCompra.metodo == "EFECTIVO",
        )
        .scalar()
    )
    total_pagos_manuales_efectivo = (
        db.query(func.coalesce(func.sum(PagoCuentaPagarManual.monto), 0))
        .filter(
            PagoCuentaPagarManual.id_turno == turno.id_turno,
            PagoCuentaPagarManual.metodo == "EFECTIVO",
        )
        .scalar()
    )
    total_gastos = (
        db.query(func.coalesce(func.sum(GastoOperativo.monto), 0))
        .filter(GastoOperativo.id_turno == turno.id_turno)
        .scalar()
    )

    esperado = (
        Decimal(turno.monto_apertura or 0)
        + Decimal(total_efectivo_cobrado)
        - Decimal(total_pagos_oc_efectivo)
        - Decimal(total_pagos_manuales_efectivo)
        - Decimal(total_gastos)
    )
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
