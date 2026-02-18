"""
Router para cuentas por pagar manuales (sin orden de compra).
Facturas, renta, servicios, etc.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.cuenta_pagar_manual import CuentaPagarManual, PagoCuentaPagarManual
from app.models.proveedor import Proveedor
from app.models.caja_turno import CajaTurno
from app.schemas.cuenta_pagar_manual import (
    CuentaPagarManualCreate,
    CuentaPagarManualUpdate,
    PagoCuentaPagarManualCreate,
)
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_decimal, money_round, to_float_money
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter(prefix="/cuentas-pagar-manuales", tags=["Cuentas por pagar manuales"])


def _nombre_acreedor(c: CuentaPagarManual) -> str:
    if c.id_proveedor:
        p = c.proveedor
        return p.nombre if p else ""
    return c.acreedor_nombre or ""


@router.get("")
def listar_cuentas(
    id_proveedor: Optional[int] = Query(None),
    fecha_desde: Optional[str] = Query(None, description="Registro desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Registro hasta (YYYY-MM-DD)"),
    incluir_saldadas: bool = Query(False, description="Incluir cuentas ya saldadas"),
    orden_por: Optional[str] = Query("fecha", description="fecha, saldo, proveedor, antiguedad"),
    direccion: Optional[str] = Query("desc", description="asc o desc"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Lista cuentas por pagar manuales con saldo pendiente."""
    query = db.query(CuentaPagarManual).options(
        joinedload(CuentaPagarManual.pagos),
        joinedload(CuentaPagarManual.proveedor),
    ).filter(CuentaPagarManual.cancelada == False)
    if id_proveedor:
        query = query.filter(CuentaPagarManual.id_proveedor == id_proveedor)
    cuentas = query.order_by(CuentaPagarManual.fecha_registro.desc()).all()

    items = []
    hoy = date.today()
    for c in cuentas:
        total_pagado = sum(to_decimal(p.monto) for p in c.pagos)
        saldo = money_round(max(Decimal("0"), to_decimal(c.monto_total) - total_pagado))
        if saldo <= 0 and not incluir_saldadas:
            continue

        fch_reg = c.fecha_registro.isoformat() if c.fecha_registro else None
        fch_venc = c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None
        fch_ref = c.fecha_vencimiento or c.fecha_registro
        dias = (hoy - fch_ref).days if fch_ref else None
        if dias is not None:
            antiguedad_rango = "0-30" if dias <= 30 else ("31-60" if dias <= 60 else "61+")
        else:
            antiguedad_rango = "-"

        if fecha_desde or fecha_hasta:
            try:
                f = c.fecha_registro
                if not f:
                    continue
                if fecha_desde and f < datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date():
                    continue
                if fecha_hasta and f > datetime.strptime(fecha_hasta[:10], "%Y-%m-%d").date():
                    continue
            except (ValueError, TypeError):
                continue

        items.append({
            "id_cuenta": c.id_cuenta,
            "concepto": c.concepto,
            "referencia_factura": getattr(c, "referencia_factura", None) or None,
            "nombre_acreedor": _nombre_acreedor(c),
            "id_proveedor": c.id_proveedor,
            "monto_total": to_float_money(c.monto_total),
            "total_pagado": to_float_money(total_pagado),
            "saldo_pendiente": to_float_money(saldo),
            "fecha_registro": fch_reg,
            "fecha_vencimiento": fch_venc,
            "dias_desde_registro": dias,
            "antiguedad_rango": antiguedad_rango,
        })

    desc = direccion and str(direccion).lower() == "desc"
    key_map = {
        "fecha": lambda x: (x.get("fecha_vencimiento") or x.get("fecha_registro") or ""),
        "saldo": lambda x: float(x.get("saldo_pendiente", 0) or 0),
        "proveedor": lambda x: (x.get("nombre_acreedor") or "").upper(),
        "antiguedad": lambda x: (x.get("dias_desde_registro") is not None and x["dias_desde_registro"]) or -1,
    }
    key_fn = key_map.get((orden_por or "fecha").lower(), key_map["fecha"])
    items.sort(key=key_fn, reverse=desc)

    aging = {"0_30": {"count": 0, "total_saldo": float(0)}, "31_60": {"count": 0, "total_saldo": float(0)}, "61_mas": {"count": 0, "total_saldo": float(0)}}
    for i in items:
        r = i.get("antiguedad_rango")
        sal = float(i.get("saldo_pendiente", 0) or 0)
        if r == "0-30":
            aging["0_30"]["count"] += 1
            aging["0_30"]["total_saldo"] += sal
        elif r == "31-60":
            aging["31_60"]["count"] += 1
            aging["31_60"]["total_saldo"] += sal
        elif r == "61+":
            aging["61_mas"]["count"] += 1
            aging["61_mas"]["total_saldo"] += sal

    total_saldo = sum(to_decimal(i["saldo_pendiente"]) for i in items)
    return {
        "items": items,
        "total_cuentas": len(items),
        "total_saldo_pendiente": to_float_money(total_saldo),
        "aging": {
            "0_30": {"count": aging["0_30"]["count"], "total_saldo": to_float_money(Decimal(str(aging["0_30"]["total_saldo"])))},
            "31_60": {"count": aging["31_60"]["count"], "total_saldo": to_float_money(Decimal(str(aging["31_60"]["total_saldo"])))},
            "61_mas": {"count": aging["61_mas"]["count"], "total_saldo": to_float_money(Decimal(str(aging["61_mas"]["total_saldo"])))},
        },
    }


@router.post("")
def crear_cuenta(
    data: CuentaPagarManualCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Crea una nueva cuenta por pagar manual."""
    if not data.id_proveedor and not (data.acreedor_nombre and data.acreedor_nombre.strip()):
        raise HTTPException(400, detail="Indique proveedor o nombre del acreedor")
    if data.id_proveedor:
        p = db.query(Proveedor).filter(Proveedor.id_proveedor == data.id_proveedor).first()
        if not p:
            raise HTTPException(404, detail="Proveedor no encontrado")

    fecha_reg = date.today()
    if data.fecha_registro:
        try:
            fecha_reg = datetime.strptime(data.fecha_registro[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    fecha_venc = None
    if data.fecha_vencimiento:
        try:
            fecha_venc = datetime.strptime(data.fecha_vencimiento[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    c = CuentaPagarManual(
        id_proveedor=data.id_proveedor,
        acreedor_nombre=(data.acreedor_nombre or "").strip() or None,
        referencia_factura=(data.referencia_factura or "").strip() or None,
        concepto=data.concepto.strip(),
        monto_total=to_decimal(str(data.monto_total)),
        fecha_registro=fecha_reg,
        fecha_vencimiento=fecha_venc,
        observaciones=(data.observaciones or "").strip() or None,
        id_usuario=current_user.id_usuario,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "CUENTA_PAGAR_MANUAL", c.id_cuenta, {"concepto": c.concepto})
    return {
        "id_cuenta": c.id_cuenta,
        "concepto": c.concepto,
        "nombre_acreedor": _nombre_acreedor(c),
        "monto_total": to_float_money(c.monto_total),
        "saldo_pendiente": to_float_money(c.monto_total),
    }


@router.get("/{id_cuenta}")
def obtener_cuenta(
    id_cuenta: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Detalle de una cuenta con historial de pagos."""
    c = db.query(CuentaPagarManual).filter(CuentaPagarManual.id_cuenta == id_cuenta).first()
    if not c:
        raise HTTPException(404, detail="Cuenta no encontrada")
    total_pagado = sum(to_decimal(p.monto) for p in c.pagos)
    saldo = money_round(max(Decimal("0"), to_decimal(c.monto_total) - total_pagado))
    pagos_list = [
        {
            "id_pago": p.id_pago,
            "monto": to_float_money(p.monto),
            "metodo": p.metodo,
            "referencia": p.referencia,
            "fecha": p.fecha.isoformat() if p.fecha else None,
        }
        for p in sorted(c.pagos, key=lambda x: x.fecha or datetime.min, reverse=True)
    ]
    return {
        "id_cuenta": c.id_cuenta,
        "concepto": c.concepto,
        "nombre_acreedor": _nombre_acreedor(c),
        "id_proveedor": c.id_proveedor,
        "monto_total": to_float_money(c.monto_total),
        "total_pagado": to_float_money(total_pagado),
        "saldo_pendiente": to_float_money(saldo),
        "fecha_registro": c.fecha_registro.isoformat() if c.fecha_registro else None,
        "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
        "referencia_factura": getattr(c, "referencia_factura", None) or None,
        "cancelada": bool(c.cancelada),
        "pagos": pagos_list,
    }


@router.put("/{id_cuenta}")
def actualizar_cuenta(
    id_cuenta: int,
    data: CuentaPagarManualUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Actualiza una cuenta (solo si no está cancelada y tiene saldo pendiente)."""
    c = db.query(CuentaPagarManual).filter(CuentaPagarManual.id_cuenta == id_cuenta).first()
    if not c:
        raise HTTPException(404, detail="Cuenta no encontrada")
    if c.cancelada:
        raise HTTPException(400, detail="No se puede editar una cuenta cancelada")
    total_pagado = sum(to_decimal(p.monto) for p in c.pagos)
    saldo = to_decimal(c.monto_total) - total_pagado
    if saldo <= 0:
        raise HTTPException(400, detail="No se puede editar una cuenta ya saldada")
    dump = data.model_dump(exclude_unset=True)
    for k, v in dump.items():
        if k == "monto_total":
            nuevo_total = to_decimal(str(v))
            if nuevo_total < total_pagado:
                raise HTTPException(400, detail=f"Monto total no puede ser menor a lo ya pagado (${total_pagado:.2f})")
            setattr(c, k, nuevo_total)
        elif k == "fecha_vencimiento":
            if v and str(v).strip():
                try:
                    setattr(c, k, datetime.strptime(str(v)[:10], "%Y-%m-%d").date())
                except (ValueError, TypeError):
                    setattr(c, k, None)
            else:
                setattr(c, k, None)
        else:
            setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return obtener_cuenta(id_cuenta, db, current_user)


@router.post("/{id_cuenta}/pagar")
def registrar_pago(
    id_cuenta: int,
    data: PagoCuentaPagarManualCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Registra un pago contra una cuenta manual."""
    c = db.query(CuentaPagarManual).filter(CuentaPagarManual.id_cuenta == id_cuenta).first()
    if not c:
        raise HTTPException(404, detail="Cuenta no encontrada")
    if c.cancelada:
        raise HTTPException(400, detail="No se pueden registrar pagos en cuentas canceladas")
    total_pagado = sum(to_decimal(p.monto) for p in c.pagos)
    saldo = to_decimal(c.monto_total) - total_pagado
    monto = to_decimal(data.monto)
    if monto > saldo:
        raise HTTPException(400, detail=f"Monto excede el saldo pendiente (${saldo:.2f})")

    id_turno = None
    if data.metodo == "EFECTIVO":
        turno = db.query(CajaTurno).filter(
            CajaTurno.id_usuario == current_user.id_usuario,
            CajaTurno.estado == "ABIERTO",
        ).first()
        if turno:
            id_turno = turno.id_turno

    pago = PagoCuentaPagarManual(
        id_cuenta=id_cuenta,
        id_usuario=current_user.id_usuario,
        id_turno=id_turno,
        monto=monto,
        metodo=data.metodo,
        referencia=(data.referencia or "").strip() or None,
        observaciones=(data.observaciones or "").strip() or None,
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "PAGO_CUENTA_MANUAL", pago.id_pago, {"monto": to_float_money(monto)})
    saldo_nuevo = money_round(saldo - monto)
    return {
        "id_pago": pago.id_pago,
        "id_cuenta": id_cuenta,
        "monto": to_float_money(pago.monto),
        "saldo_anterior": to_float_money(saldo),
        "saldo_nuevo": to_float_money(saldo_nuevo),
    }


class CancelarBody(BaseModel):
    motivo: str = Field(..., min_length=2)


@router.post("/{id_cuenta}/cancelar")
def cancelar_cuenta(
    id_cuenta: int,
    body: CancelarBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    """Cancela una cuenta (no elimina, marca como cancelada)."""
    c = db.query(CuentaPagarManual).filter(CuentaPagarManual.id_cuenta == id_cuenta).first()
    if not c:
        raise HTTPException(404, detail="Cuenta no encontrada")
    if c.cancelada:
        raise HTTPException(400, detail="La cuenta ya está cancelada")
    c.cancelada = True
    if body.motivo:
        c.observaciones = (c.observaciones or "") + f"\n[Cancelada: {body.motivo[:200]}]"
    db.commit()
    db.refresh(c)
    registrar_auditoria(db, current_user.id_usuario, "CANCELAR", "CUENTA_PAGAR_MANUAL", id_cuenta, {"motivo": body.motivo[:100]})
    return {"id_cuenta": id_cuenta, "cancelada": True}
