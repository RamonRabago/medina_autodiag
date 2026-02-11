"""CRUD de órdenes de trabajo: crear, listar, obtener, actualizar, eliminar."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.servicio import Servicio
from app.models.repuesto import Repuesto
from app.models.vehiculo import Vehiculo
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.schemas.orden_trabajo_schema import (
    OrdenTrabajoCreate,
    OrdenTrabajoUpdate,
    OrdenTrabajoResponse,
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.utils.transaction import transaction

from .helpers import generar_numero_orden
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter()
import logging

logger = logging.getLogger(__name__)


@router.post("/", response_model=OrdenTrabajoResponse, status_code=status.HTTP_201_CREATED)
def crear_orden_trabajo(
    orden_data: OrdenTrabajoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA", "TECNICO"])),
):
    """Crear una nueva orden de trabajo."""
    logger.info(f"Usuario {current_user.email} creando orden de trabajo")

    if not orden_data.servicios and not orden_data.repuestos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes agregar al menos un producto o servicio a la orden.",
        )

    if not (orden_data.diagnostico_inicial or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El diagnóstico inicial es obligatorio.",
        )
    if not (orden_data.observaciones_cliente or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las observaciones del cliente son obligatorias.",
        )

    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == orden_data.vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {orden_data.vehiculo_id} no encontrado",
        )

    cliente = db.query(Cliente).filter(Cliente.id_cliente == orden_data.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {orden_data.cliente_id} no encontrado",
        )

    if orden_data.tecnico_id:
        tecnico = db.query(Usuario).filter(
            Usuario.id_usuario == orden_data.tecnico_id,
            Usuario.rol == "TECNICO",
        ).first()
        if not tecnico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Técnico con ID {orden_data.tecnico_id} no encontrado",
            )

    with transaction(db):
        numero_orden = generar_numero_orden(db)
        cliente_proporciono = getattr(orden_data, "cliente_proporciono_refacciones", False)
        nueva_orden = OrdenTrabajo(
            numero_orden=numero_orden,
            vehiculo_id=orden_data.vehiculo_id,
            cliente_id=orden_data.cliente_id,
            tecnico_id=orden_data.tecnico_id,
            fecha_promesa=orden_data.fecha_promesa,
            prioridad=orden_data.prioridad,
            kilometraje=orden_data.kilometraje,
            diagnostico_inicial=orden_data.diagnostico_inicial,
            observaciones_cliente=orden_data.observaciones_cliente,
            observaciones_tecnico=orden_data.observaciones_tecnico,
            requiere_autorizacion=orden_data.requiere_autorizacion,
            descuento=orden_data.descuento,
            cliente_proporciono_refacciones=cliente_proporciono,
        )
        db.add(nueva_orden)
        db.flush()

        subtotal_servicios = Decimal("0.00")
        for servicio_data in orden_data.servicios:
            servicio = db.query(Servicio).filter(Servicio.id == servicio_data.servicio_id).first()
            if not servicio:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Servicio con ID {servicio_data.servicio_id} no encontrado",
                )
            precio_unitario = servicio_data.precio_unitario if servicio_data.precio_unitario else servicio.precio_base
            detalle = DetalleOrdenTrabajo(
                orden_trabajo_id=nueva_orden.id,
                servicio_id=servicio_data.servicio_id,
                descripcion=servicio_data.descripcion if servicio_data.descripcion else servicio.nombre,
                precio_unitario=precio_unitario,
                cantidad=servicio_data.cantidad,
                descuento=servicio_data.descuento,
                observaciones=servicio_data.observaciones,
            )
            detalle.calcular_subtotal()
            subtotal_servicios += detalle.subtotal
            db.add(detalle)

        subtotal_repuestos = Decimal("0.00")
        for repuesto_data in orden_data.repuestos:
            repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == repuesto_data.repuesto_id).first()
            if not repuesto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repuesto con ID {repuesto_data.repuesto_id} no encontrado",
                )
            if getattr(repuesto, "eliminado", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El repuesto '{repuesto.nombre}' está eliminado y no puede agregarse a la orden",
                )
            if not cliente_proporciono and repuesto.stock_actual < repuesto_data.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Solicitado: {repuesto_data.cantidad}",
                )
            precio_unitario = repuesto_data.precio_unitario if repuesto_data.precio_unitario is not None else repuesto.precio_venta
            detalle = DetalleRepuestoOrden(
                orden_trabajo_id=nueva_orden.id,
                repuesto_id=repuesto_data.repuesto_id,
                cantidad=repuesto_data.cantidad,
                precio_unitario=precio_unitario,
                descuento=repuesto_data.descuento,
                observaciones=repuesto_data.observaciones,
            )
            detalle.calcular_subtotal()
            subtotal_repuestos += detalle.subtotal
            db.add(detalle)

        nueva_orden.subtotal_servicios = subtotal_servicios
        nueva_orden.subtotal_repuestos = subtotal_repuestos

        if nueva_orden.fecha_promesa and nueva_orden.fecha_ingreso:
            if nueva_orden.fecha_promesa < nueva_orden.fecha_ingreso:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La fecha promesa no puede ser anterior a la fecha de ingreso",
                )

        subtotal_base = subtotal_servicios + subtotal_repuestos
        if orden_data.descuento and float(orden_data.descuento) > float(subtotal_base):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})",
            )

        nueva_orden.calcular_total()

    db.refresh(nueva_orden)
    logger.info(f"Orden de trabajo creada: {nueva_orden.numero_orden}")
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "ORDEN_TRABAJO", nueva_orden.id, {"numero": nueva_orden.numero_orden})
    return nueva_orden


@router.get("/")
def listar_ordenes_trabajo(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    prioridad: Optional[str] = Query(None, description="Filtrar por prioridad"),
    tecnico_id: Optional[int] = Query(None, description="Filtrar por técnico"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha de ingreso desde"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha de ingreso hasta"),
    buscar: Optional[str] = Query(None, description="Buscar en número de orden"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Listar órdenes de trabajo con filtros."""
    query = db.query(OrdenTrabajo)
    if estado:
        query = query.filter(OrdenTrabajo.estado == estado)
    if prioridad:
        query = query.filter(OrdenTrabajo.prioridad == prioridad)
    if tecnico_id:
        query = query.filter(OrdenTrabajo.tecnico_id == tecnico_id)
    if cliente_id:
        query = query.filter(OrdenTrabajo.cliente_id == cliente_id)
    if fecha_desde:
        query = query.filter(OrdenTrabajo.fecha_ingreso >= fecha_desde)
    if fecha_hasta:
        query = query.filter(OrdenTrabajo.fecha_ingreso <= fecha_hasta)
    if buscar:
        query = query.filter(OrdenTrabajo.numero_orden.ilike(f"%{buscar}%"))
    if current_user.rol == "TECNICO":
        query = query.filter(OrdenTrabajo.tecnico_id == current_user.id_usuario)

    total = query.count()
    ordenes = (
        query.options(
            joinedload(OrdenTrabajo.cliente),
            joinedload(OrdenTrabajo.vehiculo),
        )
        .order_by(OrdenTrabajo.fecha_ingreso.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    ids_orden = [o.id for o in ordenes]
    ventas_por_orden = {}
    if ids_orden:
        ventas_link = db.query(Venta.id_orden, Venta.id_venta).filter(
            Venta.id_orden.in_(ids_orden),
            Venta.estado != "CANCELADA",
        ).all()
        ventas_por_orden = {r[0]: r[1] for r in ventas_link}

    resultado = []
    for o in ordenes:
        id_venta = ventas_por_orden.get(o.id)
        item = {
            "id": o.id,
            "numero_orden": o.numero_orden,
            "cliente_id": o.cliente_id,
            "vehiculo_id": o.vehiculo_id,
            "tecnico_id": o.tecnico_id,
            "prioridad": o.prioridad.value if hasattr(o.prioridad, "value") else str(o.prioridad),
            "fecha_promesa": o.fecha_promesa.isoformat() if o.fecha_promesa else None,
            "cliente_nombre": o.cliente.nombre if o.cliente else None,
            "vehiculo_info": f"{o.vehiculo.marca} {o.vehiculo.modelo} {o.vehiculo.anio}" if o.vehiculo else None,
            "estado": o.estado.value if hasattr(o.estado, "value") else str(o.estado),
            "total": float(o.total),
            "requiere_autorizacion": getattr(o, "requiere_autorizacion", False),
            "autorizado": getattr(o, "autorizado", False),
            "id_venta": id_venta,
        }
        resultado.append(item)

    return {
        "ordenes": resultado,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get("/{orden_id}")
def obtener_orden_trabajo(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Obtener detalles completos de una orden de trabajo."""
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.cliente),
            joinedload(OrdenTrabajo.vehiculo),
            joinedload(OrdenTrabajo.tecnico),
            joinedload(OrdenTrabajo.usuario_autorizacion),
            joinedload(OrdenTrabajo.usuario_inicio),
            joinedload(OrdenTrabajo.usuario_finalizacion),
            joinedload(OrdenTrabajo.usuario_entrega),
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver esta orden",
        )

    estado_str = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    prioridad_str = orden.prioridad.value if hasattr(orden.prioridad, "value") else str(orden.prioridad)
    vehiculo_info = f"{orden.vehiculo.marca} {orden.vehiculo.modelo} {orden.vehiculo.anio}" if orden.vehiculo else None
    venta = db.query(Venta).filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA").first()
    id_venta = venta.id_venta if venta else None
    return {
        "id": orden.id,
        "numero_orden": orden.numero_orden,
        "vehiculo_id": orden.vehiculo_id,
        "cliente_id": orden.cliente_id,
        "tecnico_id": orden.tecnico_id,
        "fecha_ingreso": orden.fecha_ingreso.isoformat() if orden.fecha_ingreso else None,
        "fecha_promesa": orden.fecha_promesa.isoformat() if orden.fecha_promesa else None,
        "fecha_inicio": orden.fecha_inicio.isoformat() if orden.fecha_inicio else None,
        "fecha_finalizacion": orden.fecha_finalizacion.isoformat() if orden.fecha_finalizacion else None,
        "fecha_entrega": orden.fecha_entrega.isoformat() if orden.fecha_entrega else None,
        "estado": estado_str,
        "prioridad": prioridad_str,
        "diagnostico_inicial": orden.diagnostico_inicial,
        "observaciones_cliente": orden.observaciones_cliente,
        "observaciones_tecnico": orden.observaciones_tecnico,
        "subtotal_servicios": float(orden.subtotal_servicios),
        "subtotal_repuestos": float(orden.subtotal_repuestos),
        "descuento": float(orden.descuento),
        "total": float(orden.total),
        "requiere_autorizacion": orden.requiere_autorizacion,
        "cliente_proporciono_refacciones": getattr(orden, "cliente_proporciono_refacciones", False),
        "autorizado": orden.autorizado,
        "cliente_nombre": orden.cliente.nombre if orden.cliente else None,
        "vehiculo_info": vehiculo_info,
        "cliente": {"nombre": orden.cliente.nombre} if orden.cliente else None,
        "vehiculo": {"marca": orden.vehiculo.marca, "modelo": orden.vehiculo.modelo, "anio": orden.vehiculo.anio} if orden.vehiculo else None,
        "tecnico": {"nombre": orden.tecnico.nombre, "email": orden.tecnico.email} if orden.tecnico else None,
        "id_venta": id_venta,
        "usuario_autorizacion": {"nombre": u.nombre, "fecha": orden.fecha_autorizacion.isoformat()} if (u := getattr(orden, "usuario_autorizacion", None)) and orden.fecha_autorizacion else None,
        "usuario_inicio": {"nombre": u.nombre, "fecha": orden.fecha_inicio.isoformat()} if (u := getattr(orden, "usuario_inicio", None)) and orden.fecha_inicio else None,
        "usuario_finalizacion": {"nombre": u.nombre, "fecha": orden.fecha_finalizacion.isoformat()} if (u := getattr(orden, "usuario_finalizacion", None)) and orden.fecha_finalizacion else None,
        "usuario_entrega": {"nombre": u.nombre, "fecha": orden.fecha_entrega.isoformat()} if (u := getattr(orden, "usuario_entrega", None)) and orden.fecha_entrega else None,
        "detalles_servicio": [{"id": d.id, "servicio_id": d.servicio_id, "descripcion": d.descripcion, "cantidad": d.cantidad, "precio_unitario": float(d.precio_unitario), "subtotal": float(d.subtotal)} for d in (orden.detalles_servicio or [])],
        "detalles_repuesto": [{"id": d.id, "repuesto_id": d.repuesto_id, "repuesto_nombre": d.repuesto.nombre if d.repuesto else None, "repuesto_codigo": d.repuesto.codigo if d.repuesto else None, "cantidad": d.cantidad, "precio_unitario": float(d.precio_unitario), "subtotal": float(d.subtotal)} for d in (orden.detalles_repuesto or [])],
    }


@router.put("/{orden_id}", response_model=OrdenTrabajoResponse)
def actualizar_orden_trabajo(
    orden_id: int,
    orden_data: OrdenTrabajoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA", "TECNICO"])),
):
    """Actualizar una orden de trabajo."""
    logger.info(f"Usuario {current_user.email} actualizando orden ID: {orden_id}")
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para actualizar esta orden",
        )
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede actualizar una orden en estado {orden.estado}",
        )
    if orden_data.tecnico_id:
        tecnico = db.query(Usuario).filter(
            Usuario.id_usuario == orden_data.tecnico_id,
            Usuario.rol == "TECNICO",
        ).first()
        if not tecnico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Técnico con ID {orden_data.tecnico_id} no encontrado",
            )

    with transaction(db):
        update_data = orden_data.model_dump(exclude_unset=True)
        servicios_update = update_data.pop("servicios", None)
        repuestos_update = update_data.pop("repuestos", None)

        for field, value in update_data.items():
            setattr(orden, field, value)
        if orden_data.autorizado is not None and orden_data.autorizado and not orden.fecha_autorizacion:
            orden.fecha_autorizacion = datetime.now()

        estado_str = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
        if estado_str == "PENDIENTE" and (servicios_update is not None or repuestos_update is not None):
            servicios_list = servicios_update if servicios_update is not None else []
            repuestos_list = repuestos_update if repuestos_update is not None else []
            if not servicios_list and not repuestos_list:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes agregar al menos un producto o servicio a la orden.",
                )
            for d in list(orden.detalles_servicio):
                db.delete(d)
            for d in list(orden.detalles_repuesto):
                db.delete(d)
            db.flush()
            subtotal_servicios = Decimal("0.00")
            for s in servicios_list:
                sid = s.get("servicio_id") if isinstance(s, dict) else s.servicio_id
                servicio = db.query(Servicio).filter(Servicio.id == sid).first()
                if not servicio:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Servicio con ID {sid} no encontrado")
                precio_u = (s.get("precio_unitario") if isinstance(s, dict) else s.precio_unitario) or servicio.precio_base
                desc = (s.get("descripcion") if isinstance(s, dict) else s.descripcion) or servicio.nombre
                cant = s.get("cantidad", 1) if isinstance(s, dict) else s.cantidad
                descu = s.get("descuento") if isinstance(s, dict) else getattr(s, "descuento", None)
                obs = s.get("observaciones") if isinstance(s, dict) else getattr(s, "observaciones", None)
                det = DetalleOrdenTrabajo(orden_trabajo_id=orden.id, servicio_id=sid, descripcion=desc, precio_unitario=precio_u, cantidad=cant, descuento=descu or Decimal("0"), observaciones=obs)
                det.calcular_subtotal()
                subtotal_servicios += det.subtotal
                db.add(det)
            subtotal_repuestos = Decimal("0.00")
        cliente_proporciono = getattr(orden, "cliente_proporciono_refacciones", False)
        for r in repuestos_list:
            rid = r.get("repuesto_id") if isinstance(r, dict) else r.repuesto_id
            repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == rid).first()
            if not repuesto:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repuesto con ID {rid} no encontrado")
            if getattr(repuesto, "eliminado", False):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El repuesto '{repuesto.nombre}' está eliminado y no puede agregarse")
            cant = r.get("cantidad", 1) if isinstance(r, dict) else r.cantidad
            if not cliente_proporciono and repuesto.stock_actual < cant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente para {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Solicitado: {cant}",
                )
            pr_u = r.get("precio_unitario") if isinstance(r, dict) else r.precio_unitario
            precio_u = pr_u if pr_u is not None else repuesto.precio_venta
            descu = r.get("descuento") if isinstance(r, dict) else getattr(r, "descuento", None)
            obs = r.get("observaciones") if isinstance(r, dict) else getattr(r, "observaciones", None)
            det = DetalleRepuestoOrden(orden_trabajo_id=orden.id, repuesto_id=rid, cantidad=cant, precio_unitario=precio_u, descuento=descu or Decimal("0"), observaciones=obs)
            det.calcular_subtotal()
            subtotal_repuestos += det.subtotal
            db.add(det)
        orden.subtotal_servicios = subtotal_servicios
        orden.subtotal_repuestos = subtotal_repuestos

        if orden.fecha_promesa and orden.fecha_ingreso:
            if orden.fecha_promesa < orden.fecha_ingreso:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La fecha promesa no puede ser anterior a la fecha de ingreso",
                )
        subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
        if orden.descuento and float(orden.descuento) > float(subtotal_base):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})",
            )
        orden.calcular_total()

    db.refresh(orden)
    logger.info(f"Orden actualizada: {orden.numero_orden}")
    registrar_auditoria(db, current_user.id_usuario, "ACTUALIZAR", "ORDEN_TRABAJO", orden_id, {"numero": orden.numero_orden})
    return orden


@router.delete("/{orden_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_orden_trabajo(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN"])),
):
    """Eliminar permanentemente una orden de trabajo (solo órdenes CANCELADA)."""
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado != EstadoOrden.CANCELADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar órdenes canceladas",
        )
    venta_vinculada = db.query(Venta).filter(Venta.id_orden == orden.id).first()
    if venta_vinculada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una orden con venta vinculada. Cancele o desvincule la venta primero.",
        )
    numero = orden.numero_orden
    with transaction(db):
        db.delete(orden)
    registrar_auditoria(db, current_user.id_usuario, "ELIMINAR", "ORDEN_TRABAJO", orden_id, {"numero": numero})