from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.pago import Pago
from app.models.venta import Venta
from app.models.caja_turno import CajaTurno
from app.schemas.pago import PagoCreate
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_float_money
from app.utils.liquidacion_pago import evaluar_pago_contra_total
from app.services.comisiones_service import calcular_y_registrar_comisiones


router = APIRouter(
    prefix="/pagos",
    tags=["Caja / Pagos"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def registrar_pago(
    data: PagoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    # ======================================================
    # 🔒 VALIDAR TURNO ABIERTO
    # ======================================================
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if not turno:
        raise HTTPException(
            status_code=400,
            detail="No puedes registrar pagos sin un turno de caja abierto"
        )

    # ======================================================
    # 1️⃣ VALIDAR VENTA
    # ======================================================
    venta = db.query(Venta).filter(
        Venta.id_venta == data.id_venta
    ).first()

    if not venta:
        raise HTTPException(
            status_code=404,
            detail="La venta no existe"
        )

    # ======================================================
    # 2️⃣ CALCULAR TOTAL YA PAGADO
    # ======================================================
    total_pagado = db.query(
        func.coalesce(func.sum(Pago.monto), 0)
    ).filter(
        Pago.id_venta == venta.id_venta
    ).scalar()

    excede, liquida, nuevo_redondeado, total_venta_rd, nuevo_total = evaluar_pago_contra_total(
        total_pagado, data.monto, venta.total
    )

    # ======================================================
    # 3️⃣ VALIDACIONES DE NEGOCIO
    # ======================================================
    if excede:
        raise HTTPException(
            status_code=400,
            detail="El pago excede el total de la venta"
        )

    # ======================================================
    # 4️⃣ REGISTRAR PAGO (🔥 AQUÍ VA id_turno 🔥)
    # ======================================================
    pago = Pago(
        id_venta=venta.id_venta,
        id_usuario=current_user.id_usuario,
        id_turno=turno.id_turno,        # ✅ CLAVE
        metodo=data.metodo,
        monto=data.monto,
        referencia=data.referencia
    )

    db.add(pago)

    # ======================================================
    # 5️⃣ CAMBIAR ESTADO DE LA VENTA SI SE LIQUIDA
    # ======================================================
    if liquida:
        venta.estado = "PAGADA"
        calcular_y_registrar_comisiones(db, venta.id_venta)

    db.commit()
    db.refresh(pago)

    return {
        "id_pago": pago.id_pago,
        "id_turno": turno.id_turno,
        "total_pagado": to_float_money(nuevo_total),
        "estado_venta": venta.estado
    }
