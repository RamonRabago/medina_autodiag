"""
Cotizaciones de refacciones fuera de stock local (importación, compra en línea).
"""
from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cotizacion_refaccion_especial import (
    ComentarioCotizacionRefaccion,
    CompraEjecutadaCotizacionRefaccion,
    CotizacionRefaccionEspecial,
    EstadoCotizacionRefaccion,
    LineaCotizacionRefaccion,
    MetodoPagoCompraRefaccion,
    MonedaCotizacion,
    OpcionCompraLineaCotizacion,
)
from app.models.orden_trabajo import OrdenTrabajo
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.schemas.cotizacion_refaccion import (
    ComentarioCreate,
    CompraRegistradaIn,
    CompraOut,
    CotizacionRefaccionCreate,
    CotizacionRefaccionDetail,
    CotizacionRefaccionUpdate,
    CotizacionListaItem,
    LineaCreate,
    LineaUpdate,
    ListaResponse,
    OpcionCreate,
    OpcionUpdate,
)
from app.services.cotizacion_refaccion_calculo import (
    costo_unitario_mxn_opcion,
    ganancia_estimada,
    precio_sugerido_con_iva,
)
from app.utils.jwt import get_current_user
from app.utils.roles import require_roles

router = APIRouter(prefix="/cotizaciones-refaccion", tags=["Cotizaciones refacción especial"])

ROLES_TODOS = ("ADMIN", "CAJA", "EMPLEADO", "TECNICO")
ROLES_ACEPTAR = ("ADMIN", "CAJA", "EMPLEADO")  # oficina / mostrador


def _generar_numero(db: Session) -> str:
    prefix = f"COT-{date.today().strftime('%Y%m%d')}-"
    last = (
        db.query(CotizacionRefaccionEspecial)
        .filter(CotizacionRefaccionEspecial.numero.like(prefix + "%"))
        .order_by(CotizacionRefaccionEspecial.numero.desc())
        .first()
    )
    if not last:
        return prefix + "0001"
    try:
        suf = int(str(last.numero).split("-")[-1]) + 1
    except (TypeError, ValueError):
        suf = 1
    return prefix + str(suf).zfill(4)


def _margen_decimal(cot: CotizacionRefaccionEspecial) -> Optional[Decimal]:
    if cot.margen_objetivo_pct is None:
        return None
    return Decimal(str(cot.margen_objetivo_pct))


def _tc_cot_decimal(cot: CotizacionRefaccionEspecial) -> Optional[Decimal]:
    if cot.tc_referencia_usd_mxn is None:
        return None
    return Decimal(str(cot.tc_referencia_usd_mxn))


def _serialize_opcion(
    opcion: OpcionCompraLineaCotizacion,
    linea: LineaCotizacionRefaccion,
    cot: CotizacionRefaccionEspecial,
) -> dict[str, Any]:
    tc_cot = _tc_cot_decimal(cot)
    margen = _margen_decimal(cot)
    cant = Decimal(str(linea.cantidad or 1))
    d: dict[str, Any] = {
        "id": opcion.id,
        "id_linea": opcion.id_linea,
        "origen_nombre": opcion.origen_nombre,
        "url_compra": opcion.url_compra,
        "moneda": opcion.moneda.value if hasattr(opcion.moneda, "value") else str(opcion.moneda),
        "monto_unitario": Decimal(str(opcion.monto_unitario)),
        "tipo_cambio_a_mxn": Decimal(str(opcion.tipo_cambio_a_mxn)) if opcion.tipo_cambio_a_mxn is not None else None,
        "otros_costos_mxn": Decimal(str(opcion.otros_costos_mxn or 0)),
        "dias_estimados_entrega": opcion.dias_estimados_entrega,
        "notas": opcion.notas,
        "es_preferida": bool(opcion.es_preferida),
        "costo_unitario_mxn": None,
        "precio_sugerido_linea": None,
        "ganancia_estimada_linea": None,
        "costo_error": None,
    }
    try:
        cu = costo_unitario_mxn_opcion(opcion, tc_cot)
        d["costo_unitario_mxn"] = cu.quantize(Decimal("0.01"))
        ps = precio_sugerido_con_iva(cu, cant, margen, Decimal(str(settings.IVA_PORCENTAJE)))
        d["precio_sugerido_linea"] = ps
        d["ganancia_estimada_linea"] = ganancia_estimada(ps, cu, cant)
    except ValueError as e:
        d["costo_error"] = str(e)
    return d


def _serialize_linea(linea: LineaCotizacionRefaccion, cot: CotizacionRefaccionEspecial) -> dict[str, Any]:
    opciones = sorted(linea.opciones or [], key=lambda o: o.id)
    return {
        "id": linea.id,
        "id_cotizacion": linea.id_cotizacion,
        "n_linea": linea.n_linea,
        "descripcion": linea.descripcion,
        "cantidad": Decimal(str(linea.cantidad)),
        "posicion_lado": linea.posicion_lado,
        "observaciones": linea.observaciones,
        "opciones": [_serialize_opcion(o, linea, cot) for o in opciones],
    }


def _totales_cotizacion(cot: CotizacionRefaccionEspecial) -> dict[str, Any]:
    precio_total = Decimal("0")
    costo_total = Decimal("0")
    ganancia_total = Decimal("0")
    lineas_detail: List[dict] = []
    for ln in sorted(cot.lineas or [], key=lambda x: x.n_linea):
        pref = [o for o in (ln.opciones or []) if o.es_preferida]
        op_usar = pref[0] if len(pref) == 1 else (pref[0] if pref else None)
        if not op_usar and ln.opciones:
            op_usar = sorted(ln.opciones, key=lambda x: x.id)[0]
        if not op_usar:
            lineas_detail.append({"id_linea": ln.id, "subtotal_precio_sugerido": None, "costo_error": "Sin opciones"})
            continue
        ser = _serialize_opcion(op_usar, ln, cot)
        ps = ser.get("precio_sugerido_linea")
        cu = ser.get("costo_unitario_mxn")
        ge = ser.get("ganancia_estimada_linea")
        err = ser.get("costo_error")
        if err:
            lineas_detail.append({"id_linea": ln.id, "subtotal_precio_sugerido": None, "costo_error": err})
            continue
        if ps is not None:
            precio_total += ps
        if cu is not None:
            cant = Decimal(str(ln.cantidad or 1))
            costo_total += cu * cant
        if ge is not None:
            ganancia_total += ge
        lineas_detail.append(
            {
                "id_linea": ln.id,
                "subtotal_precio_sugerido": ps,
                "ganancia_estimada_linea": ge,
            }
        )
    return {
        "precio_sugerido_total": precio_total.quantize(Decimal("0.01")),
        "costo_estimado_total_mxn": costo_total.quantize(Decimal("0.01")),
        "ganancia_estimada_total": ganancia_total.quantize(Decimal("0.01")),
        "lineas": lineas_detail,
    }


def _cotizacion_to_detail(db: Session, cot: CotizacionRefaccionEspecial) -> dict[str, Any]:
    cli = db.query(Cliente).filter(Cliente.id_cliente == cot.id_cliente).first()
    cre = db.query(Usuario).filter(Usuario.id_usuario == cot.id_usuario_creo).first()
    veh_txt = None
    if cot.id_vehiculo:
        v = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == cot.id_vehiculo).first()
        if v:
            veh_txt = " ".join(
                filter(
                    None,
                    [
                        getattr(v, "marca", None) or "",
                        getattr(v, "modelo", None) or "",
                        str(getattr(v, "anio", "") or ""),
                    ],
                )
            ).strip() or None

    comentarios_out: List[dict] = []
    for c in sorted(cot.comentarios or [], key=lambda x: x.creado_en or datetime.min):
        u = db.query(Usuario).filter(Usuario.id_usuario == c.id_usuario).first()
        comentarios_out.append(
            {
                "id": c.id,
                "id_cotizacion": c.id_cotizacion,
                "id_usuario": c.id_usuario,
                "usuario_nombre": u.nombre if u else None,
                "mensaje": c.mensaje,
                "creado_en": c.creado_en,
            }
        )

    compras_out: List[dict] = []
    for cp in sorted(cot.compras_ejecutadas or [], key=lambda x: x.fecha_pago or datetime.min):
        compras_out.append(
            {
                "id": cp.id,
                "id_cotizacion": cp.id_cotizacion,
                "id_linea": cp.id_linea,
                "id_opcion": cp.id_opcion,
                "monto_pagado": cp.monto_pagado,
                "moneda": cp.moneda.value if hasattr(cp.moneda, "value") else str(cp.moneda),
                "tipo_cambio_aplicado": cp.tipo_cambio_aplicado,
                "metodo": cp.metodo.value if hasattr(cp.metodo, "value") else str(cp.metodo),
                "comprobante_url": cp.comprobante_url,
                "notas": cp.notas,
                "fecha_pago": cp.fecha_pago,
                "id_usuario_registro": cp.id_usuario_registro,
            }
        )

    lineas_out = [_serialize_linea(ln, cot) for ln in sorted(cot.lineas or [], key=lambda x: x.n_linea)]

    return {
        "id": cot.id,
        "numero": cot.numero,
        "id_cliente": cot.id_cliente,
        "cliente_nombre": cli.nombre if cli else None,
        "id_vehiculo": cot.id_vehiculo,
        "vehiculo_texto": veh_txt,
        "id_orden_trabajo": cot.id_orden_trabajo,
        "id_usuario_creo": cot.id_usuario_creo,
        "creador_nombre": cre.nombre if cre else None,
        "estado": cot.estado.value if hasattr(cot.estado, "value") else str(cot.estado),
        "notas_generales": cot.notas_generales,
        "tc_referencia_usd_mxn": cot.tc_referencia_usd_mxn,
        "margen_objetivo_pct": cot.margen_objetivo_pct,
        "congelada": bool(cot.congelada),
        "id_usuario_aceptacion": cot.id_usuario_aceptacion,
        "fecha_aceptacion_cliente": cot.fecha_aceptacion_cliente,
        "creado_en": cot.creado_en,
        "actualizado_en": cot.actualizado_en,
        "lineas": lineas_out,
        "comentarios": comentarios_out,
        "compras_ejecutadas": compras_out,
        "totales": _totales_cotizacion(cot),
    }


def _validar_cliente_vehiculo_orden(
    db: Session,
    id_cliente: int,
    id_vehiculo: Optional[int],
    id_orden: Optional[int],
) -> None:
    cl = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cl:
        raise HTTPException(404, detail="Cliente no encontrado")
    if id_vehiculo:
        v = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()
        if not v:
            raise HTTPException(404, detail="Vehículo no encontrado")
        if v.id_cliente != id_cliente:
            raise HTTPException(400, detail="El vehículo no pertenece al cliente indicado")
    if id_orden:
        o = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == id_orden).first()
        if not o:
            raise HTTPException(404, detail="Orden de trabajo no encontrada")
        if o.cliente_id != id_cliente:
            raise HTTPException(400, detail="La orden de trabajo no corresponde al cliente")


def _puede_editar_contenido(cot: CotizacionRefaccionEspecial) -> bool:
    return cot.estado == EstadoCotizacionRefaccion.BORRADOR


@router.get("/", response_model=ListaResponse)
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
    estado: Optional[str] = Query(None),
    buscar: Optional[str] = Query(None),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
):
    q = db.query(CotizacionRefaccionEspecial).order_by(CotizacionRefaccionEspecial.creado_en.desc())
    if estado:
        try:
            est = EstadoCotizacionRefaccion(estado)
            q = q.filter(CotizacionRefaccionEspecial.estado == est)
        except ValueError:
            raise HTTPException(400, detail="Estado inválido")
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        ids_clientes = [r[0] for r in db.query(Cliente.id_cliente).filter(Cliente.nombre.ilike(term)).all()]
        flt = [CotizacionRefaccionEspecial.numero.ilike(term)]
        if ids_clientes:
            flt.append(CotizacionRefaccionEspecial.id_cliente.in_(ids_clientes))
        q = q.filter(or_(*flt))

    total = q.count()
    total_paginas = max(1, math.ceil(total / limite)) if total else 1
    offset = (pagina - 1) * limite
    rows = q.offset(offset).limit(limite).all()

    items: List[CotizacionListaItem] = []
    for cot in rows:
        cli = db.query(Cliente).filter(Cliente.id_cliente == cot.id_cliente).first()
        items.append(
            CotizacionListaItem(
                id=cot.id,
                numero=cot.numero,
                id_cliente=cot.id_cliente,
                cliente_nombre=cli.nombre if cli else None,
                estado=cot.estado.value if hasattr(cot.estado, "value") else str(cot.estado),
                creado_en=cot.creado_en,
                actualizado_en=cot.actualizado_en,
            )
        )
    return ListaResponse(items=items, total=total, pagina=pagina, total_paginas=total_paginas)


@router.post("/", response_model=CotizacionRefaccionDetail, status_code=status.HTTP_201_CREATED)
def crear(
    data: CotizacionRefaccionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    _validar_cliente_vehiculo_orden(db, data.id_cliente, data.id_vehiculo, data.id_orden_trabajo)
    num = _generar_numero(db)
    cot = CotizacionRefaccionEspecial(
        numero=num,
        id_cliente=data.id_cliente,
        id_vehiculo=data.id_vehiculo,
        id_orden_trabajo=data.id_orden_trabajo,
        id_usuario_creo=current_user.id_usuario,
        estado=EstadoCotizacionRefaccion.BORRADOR,
        notas_generales=data.notas_generales,
        tc_referencia_usd_mxn=data.tc_referencia_usd_mxn,
        margen_objetivo_pct=data.margen_objetivo_pct,
        congelada=False,
    )
    db.add(cot)
    db.commit()
    db.refresh(cot)
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cot.id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.get("/{cotizacion_id}", response_model=CotizacionRefaccionDetail)
def obtener(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    return _cotizacion_to_detail(db, cot)


@router.put("/{cotizacion_id}", response_model=CotizacionRefaccionDetail)
def actualizar_cabecera(
    cotizacion_id: int,
    data: CotizacionRefaccionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo se puede editar en estado BORRADOR")
    id_cl = cot.id_cliente
    if data.id_vehiculo is not None or data.id_orden_trabajo is not None:
        _validar_cliente_vehiculo_orden(db, id_cl, data.id_vehiculo if data.id_vehiculo is not None else cot.id_vehiculo, data.id_orden_trabajo if data.id_orden_trabajo is not None else cot.id_orden_trabajo)
    if data.id_vehiculo is not None:
        cot.id_vehiculo = data.id_vehiculo
    if data.id_orden_trabajo is not None:
        cot.id_orden_trabajo = data.id_orden_trabajo
    if data.notas_generales is not None:
        cot.notas_generales = data.notas_generales
    if data.tc_referencia_usd_mxn is not None:
        cot.tc_referencia_usd_mxn = data.tc_referencia_usd_mxn
    if data.margen_objetivo_pct is not None:
        cot.margen_objetivo_pct = data.margen_objetivo_pct
    db.commit()
    db.refresh(cot)
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/lineas", response_model=CotizacionRefaccionDetail)
def agregar_linea(
    cotizacion_id: int,
    data: LineaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(joinedload(CotizacionRefaccionEspecial.lineas))
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo se pueden agregar líneas en BORRADOR")
    nxt = 1
    if cot.lineas:
        nxt = max(l.n_linea for l in cot.lineas) + 1
    ln = LineaCotizacionRefaccion(
        id_cotizacion=cot.id,
        n_linea=nxt,
        descripcion=data.descripcion.strip(),
        cantidad=data.cantidad,
        posicion_lado=data.posicion_lado,
        observaciones=data.observaciones,
    )
    db.add(ln)
    db.commit()
    db.refresh(cot)
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.put("/lineas/{linea_id}", response_model=CotizacionRefaccionDetail)
def actualizar_linea(
    linea_id: int,
    data: LineaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    ln = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == linea_id).first()
    if not ln:
        raise HTTPException(404, detail="Línea no encontrada")
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == ln.id_cotizacion).first()
    if not cot or not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo se puede editar en BORRADOR")
    if data.descripcion is not None:
        ln.descripcion = data.descripcion.strip()
    if data.cantidad is not None:
        ln.cantidad = data.cantidad
    if data.posicion_lado is not None:
        ln.posicion_lado = data.posicion_lado
    if data.observaciones is not None:
        ln.observaciones = data.observaciones
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cot.id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.delete("/lineas/{linea_id}", response_model=CotizacionRefaccionDetail)
def eliminar_linea(
    linea_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    ln = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == linea_id).first()
    if not ln:
        raise HTTPException(404, detail="Línea no encontrada")
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == ln.id_cotizacion).first()
    if not cot or not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo se puede eliminar en BORRADOR")
    cid = cot.id
    db.delete(ln)
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cid)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/lineas/{linea_id}/opciones", response_model=CotizacionRefaccionDetail)
def agregar_opcion(
    linea_id: int,
    data: OpcionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    ln = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == linea_id).first()
    if not ln:
        raise HTTPException(404, detail="Línea no encontrada")
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == ln.id_cotizacion).first()
    if not cot or not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo en BORRADOR")
    mon = MonedaCotizacion.USD if data.moneda == "USD" else MonedaCotizacion.MXN
    op = OpcionCompraLineaCotizacion(
        id_linea=ln.id,
        origen_nombre=data.origen_nombre.strip(),
        url_compra=data.url_compra.strip() if data.url_compra else None,
        moneda=mon,
        monto_unitario=data.monto_unitario,
        tipo_cambio_a_mxn=data.tipo_cambio_a_mxn,
        otros_costos_mxn=data.otros_costos_mxn or Decimal("0"),
        dias_estimados_entrega=data.dias_estimados_entrega,
        notas=data.notas,
        es_preferida=data.es_preferida,
    )
    db.add(op)
    db.flush()
    if data.es_preferida:
        for o in db.query(OpcionCompraLineaCotizacion).filter(OpcionCompraLineaCotizacion.id_linea == ln.id, OpcionCompraLineaCotizacion.id != op.id):
            o.es_preferida = False
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cot.id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.put("/opciones/{opcion_id}", response_model=CotizacionRefaccionDetail)
def actualizar_opcion(
    opcion_id: int,
    data: OpcionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    op = db.query(OpcionCompraLineaCotizacion).filter(OpcionCompraLineaCotizacion.id == opcion_id).first()
    if not op:
        raise HTTPException(404, detail="Opción no encontrada")
    ln = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == op.id_linea).first()
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == ln.id_cotizacion).first()
    if not cot or not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo en BORRADOR")
    if data.origen_nombre is not None:
        op.origen_nombre = data.origen_nombre.strip()
    if data.url_compra is not None:
        op.url_compra = data.url_compra.strip() if data.url_compra else None
    if data.moneda is not None:
        op.moneda = MonedaCotizacion.USD if data.moneda == "USD" else MonedaCotizacion.MXN
    if data.monto_unitario is not None:
        op.monto_unitario = data.monto_unitario
    if data.tipo_cambio_a_mxn is not None:
        op.tipo_cambio_a_mxn = data.tipo_cambio_a_mxn
    if data.otros_costos_mxn is not None:
        op.otros_costos_mxn = data.otros_costos_mxn
    if data.dias_estimados_entrega is not None:
        op.dias_estimados_entrega = data.dias_estimados_entrega
    if data.notas is not None:
        op.notas = data.notas
    if data.es_preferida is not None:
        op.es_preferida = data.es_preferida
        if data.es_preferida:
            for o in db.query(OpcionCompraLineaCotizacion).filter(
                OpcionCompraLineaCotizacion.id_linea == op.id_linea,
                OpcionCompraLineaCotizacion.id != op.id,
            ):
                o.es_preferida = False
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cot.id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/opciones/{opcion_id}/marcar-preferida", response_model=CotizacionRefaccionDetail)
def marcar_opcion_preferida(
    opcion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    op = db.query(OpcionCompraLineaCotizacion).filter(OpcionCompraLineaCotizacion.id == opcion_id).first()
    if not op:
        raise HTTPException(404, detail="Opción no encontrada")
    ln = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == op.id_linea).first()
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == ln.id_cotizacion).first()
    if not cot or not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo en BORRADOR")
    op.es_preferida = True
    for o in db.query(OpcionCompraLineaCotizacion).filter(
        OpcionCompraLineaCotizacion.id_linea == op.id_linea,
        OpcionCompraLineaCotizacion.id != op.id,
    ):
        o.es_preferida = False
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cot.id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.delete("/opciones/{opcion_id}", response_model=CotizacionRefaccionDetail)
def eliminar_opcion(
    opcion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    op = db.query(OpcionCompraLineaCotizacion).filter(OpcionCompraLineaCotizacion.id == opcion_id).first()
    if not op:
        raise HTTPException(404, detail="Opción no encontrada")
    ln = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == op.id_linea).first()
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == ln.id_cotizacion).first()
    if not cot or not _puede_editar_contenido(cot):
        raise HTTPException(400, detail="Solo en BORRADOR")
    cid = cot.id
    db.delete(op)
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cid)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/comentarios", response_model=CotizacionRefaccionDetail)
def agregar_comentario(
    cotizacion_id: int,
    data: ComentarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado == EstadoCotizacionRefaccion.CANCELADA:
        raise HTTPException(400, detail="Cotización cancelada")
    c = ComentarioCotizacionRefaccion(
        id_cotizacion=cot.id,
        id_usuario=current_user.id_usuario,
        mensaje=data.mensaje.strip(),
    )
    db.add(c)
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/enviar", response_model=CotizacionRefaccionDetail)
def enviar_cotizacion(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones))
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado != EstadoCotizacionRefaccion.BORRADOR:
        raise HTTPException(400, detail="Solo se puede enviar desde BORRADOR")
    if not cot.lineas:
        raise HTTPException(400, detail="Agregue al menos una línea")
    for ln in cot.lineas:
        if not ln.opciones:
            raise HTTPException(400, detail=f"Línea {ln.n_linea} sin opciones de compra")
    cot.estado = EstadoCotizacionRefaccion.ENVIADA
    cot.congelada = True
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/aceptar-cliente", response_model=CotizacionRefaccionDetail)
def aceptar_cliente(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_ACEPTAR)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado != EstadoCotizacionRefaccion.ENVIADA:
        raise HTTPException(400, detail="Solo se puede aceptar cuando está ENVIADA")
    cot.estado = EstadoCotizacionRefaccion.ACEPTADA_CLIENTE
    cot.id_usuario_aceptacion = current_user.id_usuario
    cot.fecha_aceptacion_cliente = datetime.utcnow()
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/registrar-compra", response_model=CotizacionRefaccionDetail)
def registrar_compra(
    cotizacion_id: int,
    data: CompraRegistradaIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado not in (
        EstadoCotizacionRefaccion.ACEPTADA_CLIENTE,
        EstadoCotizacionRefaccion.EN_COMPRA,
    ):
        raise HTTPException(400, detail="Registre compra solo tras aceptación del cliente")
    if data.id_linea:
        ln = db.query(LineaCotizacionRefaccion).filter(
            LineaCotizacionRefaccion.id == data.id_linea,
            LineaCotizacionRefaccion.id_cotizacion == cot.id,
        ).first()
        if not ln:
            raise HTTPException(404, detail="Línea no pertenece a la cotización")
    if data.id_opcion:
        op = db.query(OpcionCompraLineaCotizacion).filter(OpcionCompraLineaCotizacion.id == data.id_opcion).first()
        if not op:
            raise HTTPException(404, detail="Opción no encontrada")
        ln2 = db.query(LineaCotizacionRefaccion).filter(LineaCotizacionRefaccion.id == op.id_linea).first()
        if not ln2 or ln2.id_cotizacion != cot.id:
            raise HTTPException(400, detail="La opción no pertenece a esta cotización")

    try:
        met = MetodoPagoCompraRefaccion(data.metodo)
    except ValueError:
        met = MetodoPagoCompraRefaccion.OTRO
    mon = MonedaCotizacion.USD if data.moneda == "USD" else MonedaCotizacion.MXN

    cp = CompraEjecutadaCotizacionRefaccion(
        id_cotizacion=cot.id,
        id_linea=data.id_linea,
        id_opcion=data.id_opcion,
        monto_pagado=data.monto_pagado,
        moneda=mon,
        tipo_cambio_aplicado=data.tipo_cambio_aplicado,
        metodo=met,
        comprobante_url=data.comprobante_url.strip() if data.comprobante_url else None,
        notas=data.notas,
        fecha_pago=datetime.utcnow(),
        id_usuario_registro=current_user.id_usuario,
    )
    db.add(cp)
    cot.estado = EstadoCotizacionRefaccion.EN_COMPRA
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/marcar-recibida", response_model=CotizacionRefaccionDetail)
def marcar_recibida(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado != EstadoCotizacionRefaccion.EN_COMPRA:
        raise HTTPException(400, detail="Solo desde EN_COMPRA")
    cot.estado = EstadoCotizacionRefaccion.RECIBIDA
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/marcar-entregada", response_model=CotizacionRefaccionDetail)
def marcar_entregada(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado != EstadoCotizacionRefaccion.RECIBIDA:
        raise HTTPException(400, detail="Solo desde RECIBIDA")
    cot.estado = EstadoCotizacionRefaccion.ENTREGADA
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)


@router.post("/{cotizacion_id}/cancelar", response_model=CotizacionRefaccionDetail)
def cancelar(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(*ROLES_TODOS)),
):
    cot = db.query(CotizacionRefaccionEspecial).filter(CotizacionRefaccionEspecial.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(404, detail="Cotización no encontrada")
    if cot.estado in (EstadoCotizacionRefaccion.ENTREGADA, EstadoCotizacionRefaccion.CANCELADA):
        raise HTTPException(400, detail="No se puede cancelar")
    cot.estado = EstadoCotizacionRefaccion.CANCELADA
    db.commit()
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
            joinedload(CotizacionRefaccionEspecial.comentarios),
            joinedload(CotizacionRefaccionEspecial.compras_ejecutadas),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    return _cotizacion_to_detail(db, cot)
