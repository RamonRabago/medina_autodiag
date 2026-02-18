"""
Router para préstamos a empleados.
Solo ADMIN puede crear y gestionar. Empleados ven los suyos.
"""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import Optional, List

from app.database import get_db
from app.models.prestamo_empleado import PrestamoEmpleado, DescuentoPrestamo
from app.models.usuario import Usuario
from app.models.comision_devengada import ComisionDevengada
from app.services.nomina_service import calcular_nomina, DIAS_PERIODO
from app.schemas.prestamo_empleado import (
    PrestamoEmpleadoCreate,
    PrestamoEmpleadoUpdate,
    PrestamoEmpleadoOut,
    AplicarDescuentoIn,
)
from app.utils.jwt import get_current_user
from app.utils.roles import require_roles
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter(prefix="/prestamos-empleados", tags=["Préstamos empleados"])


def _saldo_pendiente(prestamo: PrestamoEmpleado, db: Session) -> Decimal:
    """Calcula saldo pendiente: monto_total - suma de descuentos aplicados."""
    total_descontado = (
        db.query(func.coalesce(func.sum(DescuentoPrestamo.monto_descontado), 0))
        .filter(DescuentoPrestamo.id_prestamo == prestamo.id)
        .scalar()
    )
    return max(Decimal("0"), Decimal(str(prestamo.monto_total)) - Decimal(str(total_descontado)))


def _prestamo_to_out(
    prestamo: PrestamoEmpleado,
    db: Session,
    incluir_empleado_nombre: bool = False,
) -> dict:
    saldo = _saldo_pendiente(prestamo, db)
    d = {
        "id": prestamo.id,
        "id_usuario": prestamo.id_usuario,
        "monto_total": prestamo.monto_total,
        "descuento_por_periodo": prestamo.descuento_por_periodo,
        "periodo_descuento": prestamo.periodo_descuento,
        "fecha_inicio": prestamo.fecha_inicio,
        "estado": prestamo.estado.value if hasattr(prestamo.estado, "value") else str(prestamo.estado),
        "observaciones": prestamo.observaciones,
        "saldo_pendiente": saldo,
    }
    if incluir_empleado_nombre:
        emp = db.query(Usuario).filter(Usuario.id_usuario == prestamo.id_usuario).first()
        d["empleado_nombre"] = emp.nombre if emp else None
    return d


# ---- ADMIN: CRUD ----
@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_prestamo(
    data: PrestamoEmpleadoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """Solo ADMIN. Crea un préstamo para un empleado."""
    empleado = db.query(Usuario).filter(Usuario.id_usuario == data.id_usuario).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    prestamo = PrestamoEmpleado(
        id_usuario=data.id_usuario,
        monto_total=data.monto_total,
        descuento_por_periodo=data.descuento_por_periodo,
        periodo_descuento=data.periodo_descuento,
        fecha_inicio=data.fecha_inicio,
        estado="ACTIVO",
        observaciones=data.observaciones,
        creado_por=current_user.id_usuario,
    )
    db.add(prestamo)
    db.commit()
    db.refresh(prestamo)
    registrar_auditoria(
        db, current_user.id_usuario, "CREAR", "PRESTAMO_EMPLEADO", prestamo.id,
        {"id_usuario": data.id_usuario, "monto": float(data.monto_total)},
    )
    return _prestamo_to_out(prestamo, db, incluir_empleado_nombre=True)


@router.get("/", response_model=List[dict])
def listar_prestamos(
    id_usuario: Optional[int] = Query(None, description="Filtrar por empleado"),
    estado: Optional[str] = Query(None, description="ACTIVO, LIQUIDADO, CANCELADO"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """Solo ADMIN. Lista todos los préstamos con filtros."""
    q = db.query(PrestamoEmpleado).order_by(PrestamoEmpleado.creado_en.desc())
    if id_usuario:
        q = q.filter(PrestamoEmpleado.id_usuario == id_usuario)
    if estado:
        q = q.filter(PrestamoEmpleado.estado == estado)
    prestamos = q.all()
    return [_prestamo_to_out(p, db, incluir_empleado_nombre=True) for p in prestamos]


@router.get("/me/mi-resumen", response_model=dict)
def mi_resumen_nomina(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    fecha_referencia: Optional[str] = Query(None, description="YYYY-MM-DD para periodo de referencia"),
    offset_periodos: int = Query(0, ge=-12, le=0, description="0=actual, -1=anterior, -2=hace dos, etc."),
):
    """
    Cualquier empleado autenticado. Ve su nómina del periodo:
    asistencia, salario proporcional, bono puntualidad, préstamos y comisiones.
    Soporta periodo_pago del usuario: SEMANAL, QUINCENAL, MENSUAL.
    """
    ref_date = None
    if fecha_referencia:
        try:
            ref_date = date.fromisoformat(fecha_referencia)
        except ValueError:
            ref_date = date.today()
    elif offset_periodos != 0:
        ref_date = date.today()

    nomina = calcular_nomina(
        db, current_user.id_usuario,
        fecha_referencia=ref_date,
        offset_periodos=offset_periodos,
    )
    if "error" in nomina:
        nomina = {}

    tipo_periodo = nomina.get("tipo_periodo", "SEMANAL")
    dias_vista = DIAS_PERIODO.get(tipo_periodo, 7)

    prestamos = db.query(PrestamoEmpleado).filter(
        PrestamoEmpleado.id_usuario == current_user.id_usuario,
        PrestamoEmpleado.estado == "ACTIVO",
    ).all()
    total_descuento_periodo = Decimal("0")
    listado = []
    for p in prestamos:
        saldo = _saldo_pendiente(p, db)
        if saldo > 0:
            periodo_prestamo = getattr(p.periodo_descuento, "value", None) or str(p.periodo_descuento)
            dias_prestamo = DIAS_PERIODO.get(periodo_prestamo, 7)
            factor = Decimal(dias_vista) / Decimal(dias_prestamo)
            descuento_este = Decimal(str(p.descuento_por_periodo)) * factor
            total_descuento_periodo += descuento_este
            listado.append({
                "id": p.id,
                "monto_total": p.monto_total,
                "descuento_por_periodo": float(descuento_este),
                "periodo_descuento": periodo_prestamo,
                "fecha_inicio": p.fecha_inicio,
                "saldo_pendiente": saldo,
            })

    total_descuento = float(total_descuento_periodo)
    salario_prop = nomina.get("salario_proporcional", 0) or 0
    bono = nomina.get("bono_puntualidad", 0) or 0

    # Comisiones devengadas del periodo de nómina
    comisiones = None
    periodo_inicio = nomina.get("periodo_inicio")
    periodo_fin = nomina.get("periodo_fin")
    if periodo_inicio and periodo_fin:
        try:
            d_ini = date.fromisoformat(periodo_inicio) if isinstance(periodo_inicio, str) else periodo_inicio
            d_fin = date.fromisoformat(periodo_fin) if isinstance(periodo_fin, str) else periodo_fin
            suma = (
                db.query(func.coalesce(func.sum(ComisionDevengada.monto_comision), 0))
                .filter(
                    ComisionDevengada.id_usuario == current_user.id_usuario,
                    ComisionDevengada.fecha_venta >= d_ini,
                    ComisionDevengada.fecha_venta <= d_fin,
                )
                .scalar()
            )
            comisiones = float(suma) if suma is not None else 0
        except (ValueError, TypeError):
            comisiones = 0

    total_bruto = salario_prop + bono + (comisiones or 0)
    total_neto = total_bruto - total_descuento

    return {
        "nombre": current_user.nombre,
        "periodo_inicio": nomina.get("periodo_inicio"),
        "periodo_fin": nomina.get("periodo_fin"),
        "tipo_periodo": tipo_periodo,
        "dias_pagados": nomina.get("dias_pagados"),
        "dias_esperados": nomina.get("dias_esperados"),
        "salario_base": nomina.get("salario_base"),
        "salario_proporcional": salario_prop,
        "bono_puntualidad": bono,
        "detalle_asistencia": nomina.get("detalle_asistencia", []),
        "prestamos_activos": listado,
        "total_descuento_este_periodo": total_descuento,
        "comisiones_periodo": comisiones,
        "total_bruto_estimado": total_bruto,
        "total_neto_estimado": total_neto,
    }


@router.get("/{id_prestamo}", response_model=dict)
def obtener_prestamo(
    id_prestamo: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """Solo ADMIN. Detalle de un préstamo con historial de descuentos."""
    prestamo = db.query(PrestamoEmpleado).filter(PrestamoEmpleado.id == id_prestamo).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    out = _prestamo_to_out(prestamo, db, incluir_empleado_nombre=True)
    descuentos = db.query(DescuentoPrestamo).filter(DescuentoPrestamo.id_prestamo == id_prestamo).order_by(DescuentoPrestamo.fecha_periodo.desc()).all()
    out["descuentos"] = [{"id": d.id, "monto_descontado": d.monto_descontado, "fecha_periodo": d.fecha_periodo} for d in descuentos]
    return out


@router.post("/{id_prestamo}/aplicar-descuento", response_model=dict)
def aplicar_descuento(
    id_prestamo: int,
    data: AplicarDescuentoIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """
    Solo ADMIN. Registra que se descontó X en el periodo (ej. semana del 10-feb).
    Si falta el empleado, se descuenta igual (regla de negocio).
    """
    prestamo = db.query(PrestamoEmpleado).filter(PrestamoEmpleado.id == id_prestamo).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    estado_str = getattr(prestamo.estado, "value", None) or str(prestamo.estado)
    if estado_str != "ACTIVO":
        raise HTTPException(status_code=400, detail="Solo se pueden aplicar descuentos a préstamos activos")
    monto = data.monto
    fecha_periodo = data.fecha_periodo
    # Evitar duplicado: mismo periodo
    existe = db.query(DescuentoPrestamo).filter(
        DescuentoPrestamo.id_prestamo == id_prestamo,
        DescuentoPrestamo.fecha_periodo == fecha_periodo,
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un descuento para este periodo")
    desc = DescuentoPrestamo(id_prestamo=id_prestamo, monto_descontado=monto, fecha_periodo=fecha_periodo)
    db.add(desc)
    saldo = _saldo_pendiente(prestamo, db)
    if Decimal(str(monto)) >= saldo:
        prestamo.estado = "LIQUIDADO"
    db.commit()
    db.refresh(desc)
    registrar_auditoria(db, current_user.id_usuario, "APLICAR_DESCUENTO", "PRESTAMO_EMPLEADO", id_prestamo, {"monto": float(monto), "fecha_periodo": str(fecha_periodo)})
    return {"ok": True, "id_descuento": desc.id, "saldo_pendiente": float(_saldo_pendiente(prestamo, db))}


@router.put("/{id_prestamo}", response_model=dict)
def actualizar_prestamo(
    id_prestamo: int,
    data: PrestamoEmpleadoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    """Solo ADMIN. Actualiza estado u observaciones de un préstamo."""
    prestamo = db.query(PrestamoEmpleado).filter(PrestamoEmpleado.id == id_prestamo).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    payload = data.model_dump(exclude_unset=True)
    if "estado" in payload:
        prestamo.estado = data.estado
    if "observaciones" in payload:
        prestamo.observaciones = data.observaciones
    db.commit()
    db.refresh(prestamo)
    registrar_auditoria(db, current_user.id_usuario, "ACTUALIZAR", "PRESTAMO_EMPLEADO", id_prestamo, {"campos": list(payload.keys())})
    return _prestamo_to_out(prestamo, db, incluir_empleado_nombre=True)
