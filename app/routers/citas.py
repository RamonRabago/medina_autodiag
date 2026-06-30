"""Router de Citas."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.cita import Cita, EstadoCita, TipoCita
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.schemas.cita import (
    CitaCreate,
    CitaEstadoPatchRequest,
    CitaEstadoPatchResponse,
    CitaUpdate,
    ReporteAsistenciaCitasOut,
)
from app.schemas.orden_trabajo_schema import OrdenTrabajoResponse
from app.services.auditoria_service import registrar as registrar_auditoria
from app.services.cita_estado_service import (
    _serializar_evento,
    aplicar_transicion_estado,
    calcular_estado_meta,
    flags_ligeros_estado,
    registrar_auditoria_correccion,
    registrar_evento_creacion,
)
from app.services.recepcion_ot_service import (
    construir_motivo_desde_cita,
    crear_ot_minima_pendiente,
    error_cita_sin_vehiculo,
    validar_cita_convertible,
    vincular_cita_a_orden,
)
from app.services.whatsapp_service import enviar_confirmacion_cita_whatsapp, whatsapp_esta_configurado
from app.utils.fechas import (
    ahora_local,
    condiciones_rango_local_naive,
    isoformat_local_naive_taller,
    isoformat_utc,
)
from app.utils.roles import require_roles
from app.utils.transaction import transaction

router = APIRouter(prefix="/citas", tags=["Citas"])


@router.get("/dashboard/proximas")
def citas_proximas_dashboard(
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    """Citas confirmadas con fecha/hora futura, para el Dashboard."""
    ahora = ahora_local()
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
        items.append(
            {
                "id_cita": c.id_cita,
                "fecha_hora": isoformat_local_naive_taller(c.fecha_hora),
                "tipo": tip,
                "estado": est,
                "motivo": c.motivo,
                "cliente_nombre": c.cliente.nombre if c.cliente else None,
                "vehiculo_info": f"{c.vehiculo.marca} {c.vehiculo.modelo} {c.vehiculo.anio}" if c.vehiculo else None,
            }
        )
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
    query = db.query(Cita).options(
        joinedload(Cita.cliente),
        joinedload(Cita.vehiculo),
    )
    if id_cliente:
        query = query.filter(Cita.id_cliente == id_cliente)
    if estado:
        query = query.filter(Cita.estado == estado)
    for cond in condiciones_rango_local_naive(Cita.fecha_hora, fecha_desde, fecha_hasta):
        query = query.filter(cond)
    total = query.count()
    order_col = Cita.fecha_hora.asc() if (orden or "asc").lower() == "asc" else Cita.fecha_hora.desc()
    citas = query.order_by(order_col).offset(skip).limit(limit).all()
    ahora = ahora_local()
    items = []
    for c in citas:
        est = c.estado.value if hasattr(c.estado, "value") else str(c.estado)
        tip = c.tipo.value if hasattr(c.tipo, "value") else str(c.tipo)
        # Vencida: fecha ya pasó y sigue CONFIRMADA (no se le dio seguimiento)
        vencida = c.fecha_hora < ahora and est == EstadoCita.CONFIRMADA.value
        items.append(
            {
                "id_cita": c.id_cita,
                "id_cliente": c.id_cliente,
                "id_vehiculo": c.id_vehiculo,
                "fecha_hora": isoformat_local_naive_taller(c.fecha_hora),
                "tipo": tip,
                "estado": est,
                "motivo": c.motivo,
                "motivo_cancelacion": getattr(c, "motivo_cancelacion", None),
                "id_orden": c.id_orden,
                "cliente_nombre": c.cliente.nombre if c.cliente else None,
                "vehiculo_info": f"{c.vehiculo.marca} {c.vehiculo.modelo} {c.vehiculo.anio}" if c.vehiculo else None,
                "vencida": vencida,
                **flags_ligeros_estado(c, current_user.rol),
            }
        )
    return {
        "citas": items,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get("/alertas")
def citas_alertas(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    """Citas vencidas (fecha pasada) que siguen CONFIRMADAS sin seguimiento."""
    ahora = ahora_local()
    citas_vencidas = (
        db.query(Cita)
        .filter(
            Cita.fecha_hora < ahora,
            Cita.estado == EstadoCita.CONFIRMADA,
        )
        .count()
    )
    return {"citas_vencidas": citas_vencidas}


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


def _query_citas_en_rango(
    db: Session,
    fecha_desde: str | None,
    fecha_hasta: str | None,
):
    query = db.query(Cita)
    for cond in condiciones_rango_local_naive(Cita.fecha_hora, fecha_desde, fecha_hasta):
        query = query.filter(cond)
    return query


@router.get("/reportes/asistencia", response_model=ReporteAsistenciaCitasOut)
def reporte_asistencia_citas(
    fecha_desde: str | None = Query(None, description="YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="YYYY-MM-DD"),
    top_clientes: int = Query(10, ge=1, le=50, description="Clientes con más inasistencias"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    """
    Resumen de citas por estado y tasa de no asistencia (base para reportes futuros).
    """

    def base():
        return _query_citas_en_rango(db, fecha_desde, fecha_hasta)

    total = base().count()
    confirmadas = base().filter(Cita.estado == EstadoCita.CONFIRMADA).count()
    asistidas = base().filter(Cita.estado == EstadoCita.SI_ASISTIO).count()
    no_asistidas = base().filter(Cita.estado == EstadoCita.NO_ASISTIO).count()
    canceladas = base().filter(Cita.estado == EstadoCita.CANCELADA).count()

    cerradas_asistencia = asistidas + no_asistidas
    porcentaje_no_asistencia = round((no_asistidas / cerradas_asistencia) * 100, 2) if cerradas_asistencia else 0.0

    q_inasist = (
        _query_citas_en_rango(db, fecha_desde, fecha_hasta)
        .join(Cliente, Cliente.id_cliente == Cita.id_cliente)
        .filter(Cita.estado == EstadoCita.NO_ASISTIO)
    )
    top_rows = (
        q_inasist.with_entities(
            Cita.id_cliente,
            Cliente.nombre,
            func.count(Cita.id_cita).label("total"),
        )
        .group_by(Cita.id_cliente, Cliente.nombre)
        .order_by(func.count(Cita.id_cita).desc())
        .limit(top_clientes)
        .all()
    )

    return ReporteAsistenciaCitasOut(
        total=total,
        confirmadas=confirmadas,
        asistidas=asistidas,
        no_asistidas=no_asistidas,
        canceladas=canceladas,
        porcentaje_no_asistencia=porcentaje_no_asistencia,
        clientes_mayor_inasistencia=[
            {
                "id_cliente": row.id_cliente,
                "nombre": row.nombre or "",
                "total_no_asistencias": int(row.total),
            }
            for row in top_rows
        ],
    )


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
        "fecha_hora": isoformat_local_naive_taller(cita.fecha_hora),
        "tipo": tip,
        "estado": est,
        "motivo": cita.motivo,
        "motivo_cancelacion": getattr(cita, "motivo_cancelacion", None),
        "notas": cita.notas,
        "id_orden": cita.id_orden,
        "estado_origen_cierre": (
            cita.estado_origen_cierre.value
            if getattr(cita, "estado_origen_cierre", None) and hasattr(cita.estado_origen_cierre, "value")
            else (str(cita.estado_origen_cierre) if getattr(cita, "estado_origen_cierre", None) else None)
        ),
        "creado_en": isoformat_utc(cita.creado_en),
        "cliente_nombre": cita.cliente.nombre if cita.cliente else None,
        "vehiculo_info": (
            f"{cita.vehiculo.marca} {cita.vehiculo.modelo} {cita.vehiculo.anio}" if cita.vehiculo else None
        ),
        "orden_vinculada": orden_info,
        "estado_meta": calcular_estado_meta(cita, current_user.rol),
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
    if data.fecha_hora <= ahora_local():
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
    db.flush()
    registrar_evento_creacion(db, cita, current_user.id_usuario)
    db.commit()
    db.refresh(cita)
    est = cita.estado.value if hasattr(cita.estado, "value") else str(cita.estado)
    tip = cita.tipo.value if hasattr(cita.tipo, "value") else str(cita.tipo)
    whatsapp_enviado = False
    mensaje_whatsapp = None
    if whatsapp_esta_configurado() and cita.fecha_hora and cliente.telefono and str(cliente.telefono).strip():
        fh = cita.fecha_hora
        fecha_txt = fh.strftime("%d/%m/%Y")
        hora_txt = fh.strftime("%H:%M")
        motivo_txt = (cita.motivo or "").strip() or tip.replace("_", " ")
        w_ok, w_err = enviar_confirmacion_cita_whatsapp(
            telefono=cliente.telefono,
            nombre_cliente=cliente.nombre or "",
            fecha_txt=fecha_txt,
            hora_txt=hora_txt,
            motivo_o_servicio=motivo_txt,
        )
        whatsapp_enviado = w_ok
        mensaje_whatsapp = None if w_ok else w_err
    out = {
        "id_cita": cita.id_cita,
        "fecha_hora": isoformat_local_naive_taller(cita.fecha_hora),
        "tipo": tip,
        "estado": est,
        "whatsapp_enviado": whatsapp_enviado,
    }
    if mensaje_whatsapp:
        out["mensaje_whatsapp"] = mensaje_whatsapp
    return out


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
    if "estado" in data_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use PATCH /api/citas/{id}/estado para cambiar el estado de la cita.",
        )
    nueva_fecha = data_dict.get("fecha_hora")
    if nueva_fecha is not None and nueva_fecha <= ahora_local():
        raise HTTPException(
            status_code=400,
            detail="La fecha y hora deben ser posteriores al momento actual",
        )
    for k, v in data_dict.items():
        if k == "tipo" and v:
            val = v.upper()
            try:
                cita.tipo = TipoCita(val)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Tipo inválido: '{v}'. Use: {', '.join(t.value for t in TipoCita)}"
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


@router.patch("/{id_cita}/estado", response_model=CitaEstadoPatchResponse)
def cambiar_estado_cita(
    id_cita: int,
    data: CitaEstadoPatchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA")),
):
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    estado_anterior = cita.estado

    with transaction(db):
        cita, evento, es_correccion = aplicar_transicion_estado(
            db,
            cita,
            estado_nuevo=data.estado_nuevo,
            id_usuario=current_user.id_usuario,
            rol=current_user.rol,
            motivo_codigo=data.motivo_codigo,
            motivo_detalle=data.motivo_detalle,
            motivo_cancelacion=data.motivo_cancelacion,
        )

    db.refresh(cita)
    if es_correccion:
        registrar_auditoria_correccion(
            db,
            id_usuario=current_user.id_usuario,
            cita=cita,
            estado_anterior=estado_anterior,
            estado_nuevo=cita.estado,
            motivo_codigo=evento.motivo_codigo,
            motivo_detalle=evento.motivo_detalle,
            correccion_con_ot=cita.id_orden is not None,
        )
    est = cita.estado.value if hasattr(cita.estado, "value") else str(cita.estado)
    origen_cierre = None
    if getattr(cita, "estado_origen_cierre", None):
        origen_cierre = (
            cita.estado_origen_cierre.value
            if hasattr(cita.estado_origen_cierre, "value")
            else str(cita.estado_origen_cierre)
        )
    return CitaEstadoPatchResponse(
        id_cita=cita.id_cita,
        estado=est,
        estado_origen_cierre=origen_cierre,
        motivo_cancelacion=getattr(cita, "motivo_cancelacion", None),
        id_orden=cita.id_orden,
        ultimo_evento=_serializar_evento(evento),
        estado_meta=calcular_estado_meta(cita, current_user.rol),
    )


@router.post("/{id_cita}/convertir-orden", response_model=OrdenTrabajoResponse, status_code=201)
def convertir_cita_a_orden(
    id_cita: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "EMPLEADO")),
):
    """
    Convierte una cita en OT mínima PENDIENTE y vincula id_orden en la misma transacción.
    Si la cita no tiene vehículo, responde 409 con redirect a recepción rápida.
    """
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    validar_cita_convertible(cita, id_cita)

    if not cita.id_vehiculo:
        raise error_cita_sin_vehiculo(id_cita)

    motivo = construir_motivo_desde_cita(cita)

    with transaction(db):
        nueva_orden = crear_ot_minima_pendiente(
            db,
            cliente_id=cita.id_cliente,
            vehiculo_id=cita.id_vehiculo,
            motivo=motivo,
            id_usuario_creo=current_user.id_usuario,
        )
        vincular_cita_a_orden(
            db,
            cita,
            nueva_orden.id,
            id_usuario=current_user.id_usuario,
            origen="CONVERTIR_OT",
        )

    db.refresh(nueva_orden)
    registrar_auditoria(
        db,
        current_user.id_usuario,
        "CITA_CONVERTIDA_OT",
        "CITA",
        id_cita,
        {
            "id_orden": nueva_orden.id,
            "numero_orden": nueva_orden.numero_orden,
        },
    )
    registrar_auditoria(
        db,
        current_user.id_usuario,
        "RECEPCION_RAPIDA",
        "ORDEN_TRABAJO",
        nueva_orden.id,
        {"numero": nueva_orden.numero_orden, "cita_id": id_cita, "via": "convertir_cita"},
    )
    return nueva_orden


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
            "La cita queda asociada para trazabilidad.",
        )
    db.delete(cita)
    db.commit()
    return None
