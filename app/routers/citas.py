"""Router de Citas."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models.cita import Cita, TipoCita, EstadoCita
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.models.orden_trabajo import OrdenTrabajo
from app.schemas.cita import CitaCreate, CitaUpdate
from app.utils.roles import require_roles

router = APIRouter(prefix="/citas", tags=["Citas"])


@router.get("/dashboard/proximas")
def citas_proximas_dashboard(
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    """Citas confirmadas con fecha/hora futura, para el Dashboard."""
    ahora = datetime.now()
    citas = (
        db.query(Cita)
        .options(
            joinedload(Cita.cliente),
            joinedload(Cita.vehiculo),
        )
        .filter(
            Cita.estado == EstadoCita.CONFIRMADA,
            Cita.fecha_hora >= ahora,
        )
        .order_by(Cita.fecha_hora.asc())
        .limit(limit)
        .all()
    )
    items = []
    for c in citas:
        est = c.estado.value if hasattr(c.estado, "value") else str(c.estado)
        tip = c.tipo.value if hasattr(c.tipo, "value") else str(c.tipo)
        items.append({
            "id_cita": c.id_cita,
            "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else None,
            "tipo": tip,
            "estado": est,
            "motivo": c.motivo,
            "cliente_nombre": c.cliente.nombre if c.cliente else None,
            "vehiculo_info": f"{c.vehiculo.marca} {c.vehiculo.modelo} {c.vehiculo.anio}" if c.vehiculo else None,
        })
    return {"citas": items, "total": len(items)}


@router.get("/")
def listar_citas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    id_cliente: int | None = Query(None, description="Filtrar por cliente"),
    estado: str | None = Query(None, description="Filtrar por estado"),
    fecha_desde: str | None = Query(None, description="YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="YYYY-MM-DD"),
    orden: str = Query("asc", description="asc = próximas primero, desc = más recientes"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    query = (
        db.query(Cita)
        .options(
            joinedload(Cita.cliente),
            joinedload(Cita.vehiculo),
        )
    )
    if id_cliente:
        query = query.filter(Cita.id_cliente == id_cliente)
    if estado:
        query = query.filter(Cita.estado == estado)
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date()
            query = query.filter(func.date(Cita.fecha_hora) >= fd)
        except (ValueError, TypeError):
            pass
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta[:10], "%Y-%m-%d").date()
            query = query.filter(func.date(Cita.fecha_hora) <= fh)
        except (ValueError, TypeError):
            pass
    total = query.count()
    order_col = Cita.fecha_hora.asc() if (orden or "asc").lower() == "asc" else Cita.fecha_hora.desc()
    citas = (
        query.order_by(order_col)
        .offset(skip)
        .limit(limit)
        .all()
    )
    items = []
    for c in citas:
        est = c.estado.value if hasattr(c.estado, "value") else str(c.estado)
        tip = c.tipo.value if hasattr(c.tipo, "value") else str(c.tipo)
        items.append({
            "id_cita": c.id_cita,
            "id_cliente": c.id_cliente,
            "id_vehiculo": c.id_vehiculo,
            "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else None,
            "tipo": tip,
            "estado": est,
            "motivo": c.motivo,
            "motivo_cancelacion": getattr(c, "motivo_cancelacion", None),
            "cliente_nombre": c.cliente.nombre if c.cliente else None,
            "vehiculo_info": f"{c.vehiculo.marca} {c.vehiculo.modelo} {c.vehiculo.anio}" if c.vehiculo else None,
        })
    return {
        "citas": items,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get("/catalogos/estados")
def listar_estados_cita(current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA"))):
    return {
        "estados": [{"valor": e.value, "nombre": e.value.replace("_", " ").title()} for e in EstadoCita],
    }


@router.get("/catalogos/tipos")
def listar_tipos_cita(current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA"))):
    return {
        "tipos": [{"valor": t.value, "nombre": t.value.title()} for t in TipoCita],
    }


@router.get("/{id_cita}")
def obtener_cita(
    id_cita: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    cita = (
        db.query(Cita)
        .options(
            joinedload(Cita.cliente),
            joinedload(Cita.vehiculo),
            joinedload(Cita.orden),
        )
        .filter(Cita.id_cita == id_cita)
        .first()
    )
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    est = cita.estado.value if hasattr(cita.estado, "value") else str(cita.estado)
    tip = cita.tipo.value if hasattr(cita.tipo, "value") else str(cita.tipo)
    orden_info = None
    if cita.orden:
        orden_info = {
            "id": cita.orden.id,
            "numero_orden": cita.orden.numero_orden,
            "estado": cita.orden.estado.value if hasattr(cita.orden.estado, "value") else str(cita.orden.estado),
        }
    return {
        "id_cita": cita.id_cita,
        "id_cliente": cita.id_cliente,
        "id_vehiculo": cita.id_vehiculo,
        "fecha_hora": cita.fecha_hora.isoformat() if cita.fecha_hora else None,
        "tipo": tip,
        "estado": est,
        "motivo": cita.motivo,
        "motivo_cancelacion": getattr(cita, "motivo_cancelacion", None),
        "notas": cita.notas,
        "id_orden": cita.id_orden,
        "creado_en": cita.creado_en.isoformat() if cita.creado_en else None,
        "cliente_nombre": cita.cliente.nombre if cita.cliente else None,
        "vehiculo_info": f"{cita.vehiculo.marca} {cita.vehiculo.modelo} {cita.vehiculo.anio}" if cita.vehiculo else None,
        "orden_vinculada": orden_info,
    }


@router.post("/", status_code=201)
def crear_cita(
    data: CitaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == data.id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if data.id_vehiculo:
        v = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == data.id_vehiculo).first()
        if not v:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        if v.id_cliente != data.id_cliente:
            raise HTTPException(status_code=400, detail="El vehículo no pertenece al cliente")
    if data.fecha_hora <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="La fecha y hora deben ser posteriores al momento actual",
        )
    tipo_val = getattr(TipoCita, data.tipo.upper(), TipoCita.REVISION) if isinstance(data.tipo, str) else data.tipo
    cita = Cita(
        id_cliente=data.id_cliente,
        id_vehiculo=data.id_vehiculo,
        fecha_hora=data.fecha_hora,
        tipo=tipo_val,
        motivo=data.motivo,
        notas=data.notas,
    )
    db.add(cita)
    db.commit()
    db.refresh(cita)
    est = cita.estado.value if hasattr(cita.estado, "value") else str(cita.estado)
    tip = cita.tipo.value if hasattr(cita.tipo, "value") else str(cita.tipo)
    return {
        "id_cita": cita.id_cita,
        "fecha_hora": cita.fecha_hora.isoformat() if cita.fecha_hora else None,
        "tipo": tip,
        "estado": est,
    }


@router.put("/{id_cita}")
def actualizar_cita(
    id_cita: int,
    data: CitaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    data_dict = data.model_dump(exclude_unset=True)
    nueva_fecha = data_dict.get("fecha_hora")
    if nueva_fecha is not None and nueva_fecha <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="La fecha y hora deben ser posteriores al momento actual",
        )
    nuevo_estado = data_dict.get("estado")
    if nuevo_estado and nuevo_estado.upper() == "CANCELADA":
        motivo_canc = data_dict.get("motivo_cancelacion") or (getattr(cita, "motivo_cancelacion", None))
        if not (motivo_canc and str(motivo_canc).strip()):
            raise HTTPException(
                status_code=400,
                detail="Al cancelar una cita debes indicar el motivo de la cancelación",
            )
    for k, v in data_dict.items():
        if k == "estado" and v:
            val = v.upper().replace("REALIZADA", "SI_ASISTIO")  # compatibilidad
            try:
                cita.estado = EstadoCita(val)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estado inválido: '{v}'. Use: {', '.join(e.value for e in EstadoCita)}"
                )
        elif k == "tipo" and v:
            val = v.upper()
            try:
                cita.tipo = TipoCita(val)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo inválido: '{v}'. Use: {', '.join(t.value for t in TipoCita)}"
                )
        elif k == "id_vehiculo":
            if v is not None:
                vh = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == v).first()
                if not vh or vh.id_cliente != cita.id_cliente:
                    raise HTTPException(status_code=400, detail="Vehículo no encontrado o no pertenece al cliente")
            cita.id_vehiculo = v
        else:
            setattr(cita, k, v)
    db.commit()
    db.refresh(cita)
    return obtener_cita(id_cita, db, current_user)


@router.delete("/{id_cita}", status_code=204)
def eliminar_cita(
    id_cita: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    if cita.id_orden is not None:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar una cita vinculada a una orden de trabajo. "
                   "La cita queda asociada para trazabilidad."
        )
    db.delete(cita)
    db.commit()
    return None
