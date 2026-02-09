from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from app.database import get_db
from app.models.pago import Pago
from app.models.caja_turno import CajaTurno
from app.models.gasto_operativo import GastoOperativo
from app.models.pago_orden_compra import PagoOrdenCompra
from app.schemas.caja_turno import TurnoAbrir, TurnoCerrar, TurnoOut
from app.services.caja_service import cerrar_turno as cerrar_turno_service
from app.utils.roles import require_roles
from app.models.caja_alerta import CajaAlerta



from app.services.caja_alertas import generar_alerta_turno_largo

router = APIRouter(
    prefix="/caja",
    tags=["Caja"]
)

# ======================================================
# 🔓 ABRIR TURNO
# ======================================================
@router.post("/abrir", response_model=TurnoOut)
def abrir_turno(
    data: TurnoAbrir,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    turno_abierto = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if turno_abierto:
        raise HTTPException(status_code=400, detail="Ya tienes un turno abierto")

    turno = CajaTurno(
        id_usuario=current_user.id_usuario,
        monto_apertura=data.monto_apertura,
        estado="ABIERTO"
    )

    db.add(turno)
    db.commit()
    db.refresh(turno)

    return turno


# ======================================================
# 🔒 CERRAR TURNO (USA SERVICIO + ALERTAS)
# ======================================================
@router.post("/cerrar", response_model=TurnoOut)
def cerrar_turno(
    data: TurnoCerrar,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if not turno:
        raise HTTPException(status_code=400, detail="No tienes un turno abierto")

    try:
        return cerrar_turno_service(
            db=db,
            id_turno=turno.id_turno,
            monto_contado=data.monto_cierre
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======================================================
# 👀 TURNO ACTUAL
# ======================================================
@router.get("/turno-actual", response_model=TurnoOut | None)
def turno_actual(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if turno:
        generar_alerta_turno_largo(db, turno)
        db.commit()

    return turno


# ======================================================
# 💰 CORTE DE CAJA POR TURNO
# ======================================================
@router.get("/corte-diario")
def corte_diario(
    fecha: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    if not fecha:
        fecha = date.today()

    turno = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if not turno:
        raise HTTPException(status_code=400, detail="No tienes un turno de caja abierto")

    resultados = (
        db.query(
            Pago.metodo,
            func.sum(Pago.monto).label("total")
        )
        .filter(Pago.id_turno == turno.id_turno)
        .group_by(Pago.metodo)
        .all()
    )

    total_general = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .filter(Pago.id_turno == turno.id_turno)
        .scalar()
    )

    total_gastos = (
        db.query(func.coalesce(func.sum(GastoOperativo.monto), 0))
        .filter(GastoOperativo.id_turno == turno.id_turno)
        .scalar()
    )

    total_pagos_proveedores = (
        db.query(func.coalesce(func.sum(PagoOrdenCompra.monto), 0))
        .filter(
            PagoOrdenCompra.id_turno == turno.id_turno,
            PagoOrdenCompra.metodo == "EFECTIVO",
        )
        .scalar()
    )

    return {
        "fecha": fecha,
        "id_turno": turno.id_turno,
        "totales_por_metodo": [
            {"metodo": metodo, "total": float(total)}
            for metodo, total in resultados
        ],
        "total_general": float(total_general),
        "total_gastos": float(total_gastos),
        "total_pagos_proveedores": float(total_pagos_proveedores),
    }


# ======================================================
# 📜 HISTÓRICO DE TURNOS
# ======================================================
@router.get("/historico-turnos")
def historico_turnos(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    query = db.query(CajaTurno).filter(CajaTurno.estado == "CERRADO")

    if current_user.rol == "CAJA":
        query = query.filter(CajaTurno.id_usuario == current_user.id_usuario)

    turnos = query.order_by(CajaTurno.fecha_cierre.desc()).all()

    return [
        {
            "id_turno": t.id_turno,
            "id_usuario": t.id_usuario,
            "fecha_apertura": t.fecha_apertura,
            "fecha_cierre": t.fecha_cierre,
            "monto_apertura": float(t.monto_apertura),
            "monto_cierre": float(t.monto_cierre),
            "estado": t.estado
        }
        for t in turnos
    ]


# ======================================================
# 🔎 DETALLE DE TURNO
# ======================================================
@router.get("/turno/{id_turno}")
def detalle_turno(
    id_turno: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    turno = db.query(CajaTurno).filter(CajaTurno.id_turno == id_turno).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    if current_user.rol == "CAJA" and turno.id_usuario != current_user.id_usuario:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este turno")

    pagos = db.query(Pago).filter(Pago.id_turno == turno.id_turno).all()

    totales = (
        db.query(Pago.metodo, func.sum(Pago.monto).label("total"))
        .filter(Pago.id_turno == turno.id_turno)
        .group_by(Pago.metodo)
        .all()
    )

    total_general = sum(float(p.monto) for p in pagos)

    gastos = db.query(GastoOperativo).filter(GastoOperativo.id_turno == turno.id_turno).all()
    total_gastos = sum(float(g.monto) for g in gastos)

    pagos_proveedores = (
        db.query(PagoOrdenCompra)
        .filter(
            PagoOrdenCompra.id_turno == turno.id_turno,
            PagoOrdenCompra.metodo == "EFECTIVO",
        )
        .order_by(PagoOrdenCompra.fecha.desc())
        .all()
    )
    total_pagos_proveedores = sum(float(p.monto) for p in pagos_proveedores)

    return {
        "turno": {
            "id_turno": turno.id_turno,
            "id_usuario": turno.id_usuario,
            "fecha_apertura": turno.fecha_apertura,
            "fecha_cierre": turno.fecha_cierre,
            "monto_apertura": float(turno.monto_apertura),
            "monto_cierre": float(turno.monto_cierre) if turno.monto_cierre else None,
            "estado": turno.estado
        },
        "pagos": [
            {
                "id_pago": p.id_pago,
                "id_venta": p.id_venta,
                "metodo": p.metodo,
                "monto": float(p.monto),
                "referencia": p.referencia,
                "fecha": p.fecha
            }
            for p in pagos
        ],
        "totales_por_metodo": [
            {"metodo": metodo, "total": float(total)}
            for metodo, total in totales
        ],
        "total_general": total_general,
        "gastos": [
            {"id_gasto": g.id_gasto, "fecha": str(g.fecha), "concepto": g.concepto, "monto": float(g.monto), "categoria": g.categoria}
            for g in gastos
        ],
        "total_gastos": total_gastos,
        "pagos_proveedores": [
            {
                "id_pago": p.id_pago,
                "id_orden_compra": p.id_orden_compra,
                "monto": float(p.monto),
                "referencia": p.referencia,
                "fecha": p.fecha,
            }
            for p in pagos_proveedores
        ],
        "total_pagos_proveedores": total_pagos_proveedores,
    }


# ======================================================
# 🚨 CIERRE FORZADO DE TURNO (ADMIN)
# ======================================================
@router.post("/cerrar-forzado/{id_turno}")
def cerrar_turno_forzado(
    id_turno: int,
    monto_cierre: float,
    motivo: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_turno == id_turno,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno abierto no encontrado")

    turno.monto_cierre = monto_cierre
    turno.fecha_cierre = func.now()
    turno.estado = "CERRADO"

    if hasattr(turno, "cerrado_por"):
        turno.cerrado_por = current_user.id_usuario
    if hasattr(turno, "motivo_cierre"):
        turno.motivo_cierre = motivo or "Cierre forzado por ADMIN"

    db.commit()
    db.refresh(turno)

    return {
        "mensaje": "Turno cerrado forzadamente",
        "id_turno": turno.id_turno,
        "cerrado_por": current_user.id_usuario,
        "motivo": motivo,
        "fecha_cierre": turno.fecha_cierre
    }
# ======================================================
# ⚠️ ALERTAS DEL CAJERO (TURNO ACTUAL)
# ======================================================
@router.get("/alertas")
def alertas_cajero(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("CAJA", "ADMIN"))
):
    # 1️⃣ Turno abierto del usuario
    turno = db.query(CajaTurno).filter(
        CajaTurno.id_usuario == current_user.id_usuario,
        CajaTurno.estado == "ABIERTO"
    ).first()

    if not turno:
        return []

    # 2️⃣ Alertas NO resueltas de ese turno
    alertas = db.query(CajaAlerta).filter(
        CajaAlerta.id_turno == turno.id_turno,
        CajaAlerta.resuelta == False
    ).all()

    # 3️⃣ Respuesta simple para UI
    return [
        {
            "id_alerta": a.id_alerta,
            "tipo": a.tipo,
            "nivel": a.nivel,
            "mensaje": a.mensaje
        }
        for a in alertas
    ]
