# app/routers/ordenes_trabajo.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden, PrioridadOrden
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.servicio import Servicio
from app.models.repuesto import Repuesto
from app.models.vehiculo import Vehiculo
from app.models.cliente import Cliente
from app.models.usuario import Usuario
from app.models.movimiento_inventario import TipoMovimiento
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.inventario_service import InventarioService
from app.models.venta import Venta
from app.schemas.orden_trabajo_schema import (
    OrdenTrabajoCreate, OrdenTrabajoUpdate, OrdenTrabajoResponse, 
    OrdenTrabajoListResponse, IniciarOrdenRequest, FinalizarOrdenRequest,
    EntregarOrdenRequest, AutorizarOrdenRequest, AgregarServicioRequest,
    AgregarRepuestoRequest
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
import logging

router = APIRouter(prefix="/ordenes-trabajo", tags=["Órdenes - Órdenes de Trabajo"])
logger = logging.getLogger(__name__)

def generar_numero_orden(db: Session) -> str:
    """
    Genera un número de orden único en formato: OT-YYYYMMDD-NNNN
    """
    fecha_hoy = datetime.now()
    prefijo = f"OT-{fecha_hoy.strftime('%Y%m%d')}"
    
    # Buscar el último número del día
    ultima_orden = db.query(OrdenTrabajo).filter(
        OrdenTrabajo.numero_orden.like(f"{prefijo}-%")
    ).order_by(OrdenTrabajo.numero_orden.desc()).first()
    
    if ultima_orden:
        # Extraer el número secuencial y sumar 1
        ultimo_num = int(ultima_orden.numero_orden.split('-')[-1])
        nuevo_num = ultimo_num + 1
    else:
        nuevo_num = 1
    
    return f"{prefijo}-{nuevo_num:04d}"

@router.post("/", response_model=OrdenTrabajoResponse, status_code=status.HTTP_201_CREATED)
def crear_orden_trabajo(
    orden_data: OrdenTrabajoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA", "TECNICO"]))
):
    """
    Crear una nueva orden de trabajo
    - **ADMIN, CAJA, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} creando orden de trabajo")

    if not orden_data.servicios and not orden_data.repuestos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes agregar al menos un producto o servicio a la orden."
        )
    
    if not (orden_data.diagnostico_inicial or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El diagnóstico inicial es obligatorio."
        )
    if not (orden_data.observaciones_cliente or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las observaciones del cliente son obligatorias."
        )
    
    # Validar que el vehículo existe
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == orden_data.vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {orden_data.vehiculo_id} no encontrado"
        )
    
    # Validar que el cliente existe
    cliente = db.query(Cliente).filter(Cliente.id_cliente == orden_data.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente con ID {orden_data.cliente_id} no encontrado"
        )
    
    # Validar técnico si se proporciona
    if orden_data.tecnico_id:
        tecnico = db.query(Usuario).filter(
            Usuario.id_usuario == orden_data.tecnico_id,
            Usuario.rol == "TECNICO"
        ).first()
        if not tecnico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Técnico con ID {orden_data.tecnico_id} no encontrado"
            )
    
    # Generar número de orden
    numero_orden = generar_numero_orden(db)
    
    # Crear orden
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
        cliente_proporciono_refacciones=cliente_proporciono
    )
    
    db.add(nueva_orden)
    db.flush()  # Para obtener el ID de la orden
    
    # Agregar servicios
    subtotal_servicios = Decimal('0.00')
    for servicio_data in orden_data.servicios:
        servicio = db.query(Servicio).filter(Servicio.id == servicio_data.servicio_id).first()
        if not servicio:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Servicio con ID {servicio_data.servicio_id} no encontrado"
            )
        
        # Usar precio del catálogo si no se proporciona uno personalizado
        precio_unitario = servicio_data.precio_unitario if servicio_data.precio_unitario else servicio.precio_base
        
        detalle = DetalleOrdenTrabajo(
            orden_trabajo_id=nueva_orden.id,
            servicio_id=servicio_data.servicio_id,
            descripcion=servicio_data.descripcion if servicio_data.descripcion else servicio.nombre,
            precio_unitario=precio_unitario,
            cantidad=servicio_data.cantidad,
            descuento=servicio_data.descuento,
            observaciones=servicio_data.observaciones
        )
        detalle.calcular_subtotal()
        subtotal_servicios += detalle.subtotal
        db.add(detalle)
    
    # Agregar repuestos
    subtotal_repuestos = Decimal('0.00')
    for repuesto_data in orden_data.repuestos:
        repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == repuesto_data.repuesto_id).first()
        if not repuesto:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repuesto con ID {repuesto_data.repuesto_id} no encontrado"
            )
        if getattr(repuesto, "eliminado", False):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El repuesto '{repuesto.nombre}' está eliminado y no puede agregarse a la orden"
            )
        
        # Verificar stock solo si el taller provee las refacciones (orden sin checkbox "cliente proporcionó")
        if not cliente_proporciono and repuesto.stock_actual < repuesto_data.cantidad:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Solicitado: {repuesto_data.cantidad}"
            )
        
        # Usar precio de venta del catálogo si no se proporciona
        precio_unitario = repuesto_data.precio_unitario if repuesto_data.precio_unitario is not None else repuesto.precio_venta
        
        detalle = DetalleRepuestoOrden(
            orden_trabajo_id=nueva_orden.id,
            repuesto_id=repuesto_data.repuesto_id,
            cantidad=repuesto_data.cantidad,
            precio_unitario=precio_unitario,
            descuento=repuesto_data.descuento,
            observaciones=repuesto_data.observaciones
        )
        detalle.calcular_subtotal()
        subtotal_repuestos += detalle.subtotal
        db.add(detalle)
    
    # Calcular totales
    nueva_orden.subtotal_servicios = subtotal_servicios
    nueva_orden.subtotal_repuestos = subtotal_repuestos

    # Validar fecha_promesa >= fecha_ingreso
    if nueva_orden.fecha_promesa and nueva_orden.fecha_ingreso:
        if nueva_orden.fecha_promesa < nueva_orden.fecha_ingreso:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha promesa no puede ser anterior a la fecha de ingreso"
            )

    # Validar descuento <= subtotal_servicios + subtotal_repuestos
    subtotal_base = subtotal_servicios + subtotal_repuestos
    if orden_data.descuento and float(orden_data.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})"
        )

    nueva_orden.calcular_total()

    db.commit()
    db.refresh(nueva_orden)

    logger.info(f"Orden de trabajo creada: {nueva_orden.numero_orden}")
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
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar órdenes de trabajo con filtros
    """
    query = db.query(OrdenTrabajo)
    
    # Filtros
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
    
    # Si es técnico, solo ver sus órdenes
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
            Venta.estado != "CANCELADA"
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
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1
    }

@router.get("/{orden_id}")
def obtener_orden_trabajo(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener detalles completos de una orden de trabajo (incluye cliente, vehículo, técnico).
    """
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.cliente),
            joinedload(OrdenTrabajo.vehiculo),
            joinedload(OrdenTrabajo.tecnico),
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver esta orden"
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
        "detalles_servicio": [{"id": d.id, "servicio_id": d.servicio_id, "descripcion": d.descripcion, "cantidad": d.cantidad, "precio_unitario": float(d.precio_unitario), "subtotal": float(d.subtotal)} for d in (orden.detalles_servicio or [])],
        "detalles_repuesto": [{"id": d.id, "repuesto_id": d.repuesto_id, "repuesto_nombre": d.repuesto.nombre if d.repuesto else None, "repuesto_codigo": d.repuesto.codigo if d.repuesto else None, "cantidad": d.cantidad, "precio_unitario": float(d.precio_unitario), "subtotal": float(d.subtotal)} for d in (orden.detalles_repuesto or [])],
    }





@router.put("/{orden_id}", response_model=OrdenTrabajoResponse)
def actualizar_orden_trabajo(
    orden_id: int,
    orden_data: OrdenTrabajoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA", "TECNICO"]))
):
    """
    Actualizar una orden de trabajo
    - **ADMIN, CAJA, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} actualizando orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # Técnicos solo actualizan sus órdenes
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para actualizar esta orden"
        )
    
    # No se pueden actualizar órdenes entregadas o canceladas
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede actualizar una orden en estado {orden.estado}"
        )
    
    # Validar técnico si se actualiza
    if orden_data.tecnico_id:
        tecnico = db.query(Usuario).filter(
            Usuario.id_usuario == orden_data.tecnico_id,
            Usuario.rol == "TECNICO"
        ).first()
        if not tecnico:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Técnico con ID {orden_data.tecnico_id} no encontrado"
            )
    
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
                detail="Debes agregar al menos un producto o servicio a la orden."
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
                db.rollback()
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
                db.rollback()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repuesto con ID {rid} no encontrado")
            if getattr(repuesto, "eliminado", False):
                db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El repuesto '{repuesto.nombre}' está eliminado y no puede agregarse")
            cant = r.get("cantidad", 1) if isinstance(r, dict) else r.cantidad
            if not cliente_proporciono and repuesto.stock_actual < cant:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stock insuficiente para {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Solicitado: {cant}")
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

    # Validar fecha_promesa >= fecha_ingreso
    if orden.fecha_promesa and orden.fecha_ingreso:
        if orden.fecha_promesa < orden.fecha_ingreso:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha promesa no puede ser anterior a la fecha de ingreso"
            )

    # Validar descuento <= subtotal_servicios + subtotal_repuestos
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})"
        )

    orden.calcular_total()

    db.commit()
    db.refresh(orden)

    logger.info(f"Orden actualizada: {orden.numero_orden}")
    return orden

@router.post("/{orden_id}/iniciar", response_model=OrdenTrabajoResponse)
def iniciar_orden_trabajo(
    orden_id: int,
    request: IniciarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"]))
):
    """
    Iniciar el trabajo en una orden (cambiar estado a EN_PROCESO)
    - **ADMIN, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} iniciando orden ID: {orden_id}")
    
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # Validar estado
    if orden.estado not in ["PENDIENTE", "ESPERANDO_AUTORIZACION"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede iniciar una orden en estado {orden.estado}"
        )
    
    # Si requiere autorización, debe estar autorizada
    if orden.requiere_autorizacion and not orden.autorizado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La orden requiere autorización del cliente antes de iniciar"
        )
    
    # Descontar repuestos del inventario al iniciar (el técnico toma las piezas)
    # Usa InventarioService para costo con precio_compra (CPP) = utilidad real correcta
    if not getattr(orden, "cliente_proporciono_refacciones", False):
        for detalle_repuesto in orden.detalles_repuesto or []:
            repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == detalle_repuesto.repuesto_id).first()
            if not repuesto:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repuesto con ID {detalle_repuesto.repuesto_id} no encontrado")
            if repuesto.stock_actual < detalle_repuesto.cantidad:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stock insuficiente de {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Necesario: {detalle_repuesto.cantidad}")
            try:
                InventarioService.registrar_movimiento(
                    db,
                    MovimientoInventarioCreate(
                        id_repuesto=repuesto.id_repuesto,
                        tipo_movimiento=TipoMovimiento.SALIDA,
                        cantidad=detalle_repuesto.cantidad,
                        precio_unitario=None,  # usa repuesto.precio_compra (CPP) para costo/utilidad
                        referencia=orden.numero_orden,
                        motivo=f"Inicio orden de trabajo {orden.numero_orden}",
                    ),
                    current_user.id_usuario,
                )
            except ValueError as e:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # Asignar técnico si no tiene (solo si quien inicia es TECNICO: se auto-asigna)
    if not orden.tecnico_id and current_user.rol == "TECNICO":
        orden.tecnico_id = current_user.id_usuario
    
    if not orden.tecnico_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe asignar un técnico a la orden antes de iniciarla. Edita la orden y asigna un técnico."
        )
    
    # Cambiar estado
    orden.estado = EstadoOrden.EN_PROCESO
    orden.fecha_inicio = datetime.now()
    
    if request.observaciones_inicio:
        orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + f"\n[Inicio] {request.observaciones_inicio}"
    
    db.commit()
    db.refresh(orden)
    
    logger.info(f"Orden iniciada: {orden.numero_orden}")
    return orden

@router.post("/{orden_id}/finalizar", response_model=OrdenTrabajoResponse)
def finalizar_orden_trabajo(
    orden_id: int,
    request: FinalizarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"]))
):
    """
    Finalizar el trabajo en una orden (cambiar estado a COMPLETADA)
    También descontará del inventario los repuestos utilizados
    - **ADMIN, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} finalizando orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # Técnicos solo finalizan sus órdenes
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para finalizar esta orden"
        )
    
    # Validar estado
    if orden.estado != "EN_PROCESO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden finalizar órdenes en proceso (estado actual: {orden.estado})"
        )
    
    # El stock ya se descontó al INICIAR la orden
    # Cambiar estado
    orden.estado = EstadoOrden.COMPLETADA
    orden.fecha_finalizacion = datetime.now()
    
    if request.observaciones_finalizacion:
        orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + f"\n[Finalización] {request.observaciones_finalizacion}"
    
    db.commit()
    db.refresh(orden)
    
    logger.info(f"Orden finalizada: {orden.numero_orden}")
    return orden

@router.post("/{orden_id}/entregar", response_model=OrdenTrabajoResponse)
def entregar_orden_trabajo(
    orden_id: int,
    request: EntregarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"]))
):
    """
    Entregar la orden al cliente (cambiar estado a ENTREGADA)
    - **ADMIN, CAJA**
    """
    logger.info(f"Usuario {current_user.email} entregando orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # Validar estado
    if orden.estado != "COMPLETADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden entregar órdenes completadas (estado actual: {orden.estado})"
        )
    
    # Cambiar estado
    orden.estado = EstadoOrden.ENTREGADA
    orden.fecha_entrega = datetime.now()
    orden.observaciones_entrega = request.observaciones_entrega
    
    db.commit()
    db.refresh(orden)
    
    logger.info(f"Orden entregada: {orden.numero_orden}")
    return orden

@router.post("/{orden_id}/cancelar", response_model=OrdenTrabajoResponse)
def cancelar_orden_trabajo(
    orden_id: int,
    motivo: str = Query(..., min_length=10, description="Motivo de la cancelación"),
    devolver_repuestos: bool = Query(False, description="Devolver repuestos al inventario (solo órdenes EN_PROCESO, repuestos no utilizados)"),
    motivo_no_devolucion: Optional[str] = Query(None, description="Motivo por el que no se devuelven (DAÑADO, USADO, MERMA, OTRO) para registro"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"]))
):
    """
    Cancelar una orden de trabajo.
    Si la orden está EN_PROCESO y devolver_repuestos=True, los repuestos del taller se devuelven al inventario.
    - **ADMIN, CAJA**
    """
    logger.info(f"Usuario {current_user.email} cancelando orden ID: {orden_id}")
    
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    if orden.estado == "ENTREGADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar una orden ya entregada"
        )
    
    estado_str = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    cliente_proporciono = getattr(orden, "cliente_proporciono_refacciones", False)
    
    if devolver_repuestos and estado_str == "EN_PROCESO" and not cliente_proporciono and orden.detalles_repuesto:
        for detalle_repuesto in orden.detalles_repuesto:
            try:
                InventarioService.registrar_movimiento(
                    db,
                    MovimientoInventarioCreate(
                        id_repuesto=detalle_repuesto.repuesto_id,
                        tipo_movimiento=TipoMovimiento.ENTRADA,
                        cantidad=detalle_repuesto.cantidad,
                        precio_unitario=None,  # usa precio_compra (CPP) para consistencia contable
                        referencia=orden.numero_orden,
                        motivo=f"Cancelación orden {orden.numero_orden} - repuestos no utilizados",
                    ),
                    current_user.id_usuario,
                )
            except ValueError as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e))
        logger.info(f"Repuestos devueltos al inventario por cancelación de orden {orden.numero_orden}")
    
    orden.estado = EstadoOrden.CANCELADA
    orden.motivo_cancelacion = motivo
    orden.fecha_cancelacion = datetime.utcnow()
    orden.id_usuario_cancelacion = current_user.id_usuario
    obs_cancel = f"\n[CANCELADA] {motivo}"
    if estado_str == "EN_PROCESO" and not devolver_repuestos and motivo_no_devolucion and orden.detalles_repuesto:
        repuestos_txt = ", ".join([
            f"{(d.repuesto.nombre if d.repuesto else f'Repuesto #{d.repuesto_id}')} x{d.cantidad}"
            for d in orden.detalles_repuesto
        ])
        obs_cancel += f". Repuestos no devueltos ({motivo_no_devolucion}): {repuestos_txt}"
    orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + obs_cancel
    
    db.commit()
    db.refresh(orden)
    
    logger.info(f"Orden cancelada: {orden.numero_orden}")
    return orden


@router.delete("/{orden_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_orden_trabajo(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN"]))
):
    """
    Eliminar permanentemente una orden de trabajo (solo órdenes CANCELADA).
    - **Solo ADMIN**
    """
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    if orden.estado != EstadoOrden.CANCELADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar órdenes canceladas"
        )

    # No eliminar si hay venta vinculada (evitar ventas huérfanas)
    venta_vinculada = db.query(Venta).filter(Venta.id_orden == orden.id).first()
    if venta_vinculada:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una orden con venta vinculada. Cancele o desvincule la venta primero."
        )

    db.delete(orden)
    db.commit()


@router.post("/{orden_id}/autorizar", response_model=OrdenTrabajoResponse)
def autorizar_orden_trabajo(
    orden_id: int,
    request: AutorizarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"]))
):
    """
    Autorizar (o rechazar) una orden de trabajo que requiere aprobación del cliente
    - **ADMIN, CAJA**
    """
    logger.info(f"Usuario {current_user.email} {'autorizando' if request.autorizado else 'rechazando'} orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    if not orden.requiere_autorizacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta orden no requiere autorización"
        )
    
    orden.autorizado = request.autorizado
    orden.fecha_autorizacion = datetime.utcnow()
    
    if request.autorizado:
        orden.estado = EstadoOrden.PENDIENTE
    else:
        # Rechazo definitivo: cancelar la orden (no se ejecutará el trabajo)
        orden.estado = EstadoOrden.CANCELADA
        orden.motivo_cancelacion = (request.observaciones or "Rechazada por el cliente").strip()
        orden.fecha_cancelacion = datetime.utcnow()
        orden.id_usuario_cancelacion = current_user.id_usuario
    
    if request.observaciones:
        orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + f"\n[Autorización] {request.observaciones}"
    
    db.commit()
    db.refresh(orden)
    
    logger.info(f"Orden {'autorizada' if request.autorizado else 'rechazada'}: {orden.numero_orden}")
    return orden














@router.post("/{orden_id}/servicios", response_model=OrdenTrabajoResponse)
def agregar_servicio_a_orden(
    orden_id: int,
    servicio_data: AgregarServicioRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"]))
):
    """
    Agregar un servicio a una orden de trabajo existente
    - **ADMIN, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} agregando servicio a orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # No se pueden agregar servicios a órdenes entregadas o canceladas
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden agregar servicios a una orden en estado {orden.estado}"
        )
    
    # Validar servicio
    servicio = db.query(Servicio).filter(Servicio.id == servicio_data.servicio_id).first()
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {servicio_data.servicio_id} no encontrado"
        )
    
    # Usar precio del catálogo si no se proporciona
    precio_unitario = servicio_data.precio_unitario if servicio_data.precio_unitario else servicio.precio_base
    
    # Crear detalle
    detalle = DetalleOrdenTrabajo(
        orden_trabajo_id=orden.id,
        servicio_id=servicio_data.servicio_id,
        descripcion=servicio_data.descripcion if servicio_data.descripcion else servicio.nombre,
        precio_unitario=precio_unitario,
        cantidad=servicio_data.cantidad,
        descuento=servicio_data.descuento,
        observaciones=servicio_data.observaciones
    )
    detalle.calcular_subtotal()
    db.add(detalle)
    
    # Recalcular totales
    orden.subtotal_servicios += detalle.subtotal
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})"
        )
    orden.calcular_total()

    db.commit()
    db.refresh(orden)

    logger.info(f"Servicio agregado a orden: {orden.numero_orden}")
    return orden

@router.delete("/{orden_id}/servicios/{detalle_id}", response_model=OrdenTrabajoResponse)
def eliminar_servicio_de_orden(
    orden_id: int,
    detalle_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"]))
):
    """
    Eliminar un servicio de una orden de trabajo
    - **ADMIN, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} eliminando servicio {detalle_id} de orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # No se pueden eliminar servicios de órdenes entregadas o canceladas
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden eliminar servicios de una orden en estado {orden.estado}"
        )
    
    # Buscar detalle
    detalle = db.query(DetalleOrdenTrabajo).filter(
        DetalleOrdenTrabajo.id == detalle_id,
        DetalleOrdenTrabajo.orden_trabajo_id == orden_id
    ).first()
    
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {detalle_id} no encontrado en la orden"
        )
    
    # Restar del subtotal
    orden.subtotal_servicios -= detalle.subtotal

    # Eliminar detalle
    db.delete(detalle)

    # Validar descuento <= subtotal tras eliminar
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tras eliminar, el descuento excede el subtotal. Reduzca el descuento a máximo {float(subtotal_base):.2f}"
        )
    orden.calcular_total()

    db.commit()
    db.refresh(orden)

    logger.info(f"Servicio eliminado de orden: {orden.numero_orden}")
    return orden

@router.post("/{orden_id}/repuestos", response_model=OrdenTrabajoResponse)
def agregar_repuesto_a_orden(
    orden_id: int,
    repuesto_data: AgregarRepuestoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"]))
):
    """
    Agregar un repuesto a una orden de trabajo existente
    - **ADMIN, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} agregando repuesto a orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # No se pueden agregar repuestos a órdenes entregadas o canceladas
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden agregar repuestos a una orden en estado {orden.estado}"
        )
    
    # Validar repuesto
    repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == repuesto_data.repuesto_id).first()
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {repuesto_data.repuesto_id} no encontrado"
        )
    if getattr(repuesto, "eliminado", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El repuesto '{repuesto.nombre}' está eliminado y no puede agregarse"
        )
    
    cliente_proporciono = getattr(orden, "cliente_proporciono_refacciones", False)
    estado_str = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    if not cliente_proporciono and repuesto.stock_actual < repuesto_data.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente para '{repuesto.nombre}'. Disponible: {repuesto.stock_actual}, Solicitado: {repuesto_data.cantidad}"
        )
    
    precio_unitario = repuesto_data.precio_unitario if repuesto_data.precio_unitario is not None else repuesto.precio_venta
    
    detalle = DetalleRepuestoOrden(
        orden_trabajo_id=orden.id,
        repuesto_id=repuesto_data.repuesto_id,
        cantidad=repuesto_data.cantidad,
        precio_unitario=precio_unitario,
        descuento=repuesto_data.descuento,
        observaciones=repuesto_data.observaciones
    )
    detalle.calcular_subtotal()
    db.add(detalle)
    
    # Descontar stock si orden EN_PROCESO y taller provee refacciones (el técnico toma la pieza)
    if estado_str == "EN_PROCESO" and not cliente_proporciono:
        try:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=repuesto.id_repuesto,
                    tipo_movimiento=TipoMovimiento.SALIDA,
                    cantidad=repuesto_data.cantidad,
                    precio_unitario=None,
                    referencia=orden.numero_orden,
                    motivo=f"Repuesto agregado a orden en proceso {orden.numero_orden}",
                ),
                current_user.id_usuario,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    # Recalcular totales
    orden.subtotal_repuestos += detalle.subtotal
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})"
        )
    orden.calcular_total()

    db.commit()
    db.refresh(orden)

    logger.info(f"Repuesto agregado a orden: {orden.numero_orden}")
    return orden

@router.delete("/{orden_id}/repuestos/{detalle_id}", response_model=OrdenTrabajoResponse)
def eliminar_repuesto_de_orden(
    orden_id: int,
    detalle_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"]))
):
    """
    Eliminar un repuesto de una orden de trabajo
    - **ADMIN, TECNICO**
    """
    logger.info(f"Usuario {current_user.email} eliminando repuesto {detalle_id} de orden ID: {orden_id}")
    
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada"
        )
    
    # No se pueden eliminar repuestos de órdenes completadas o entregadas
    if orden.estado in ["COMPLETADA", "ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden eliminar repuestos de una orden en estado {orden.estado}"
        )
    
    # Buscar detalle
    detalle = db.query(DetalleRepuestoOrden).filter(
        DetalleRepuestoOrden.id == detalle_id,
        DetalleRepuestoOrden.orden_trabajo_id == orden_id
    ).first()
    
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {detalle_id} no encontrado en la orden"
        )
    
    # Restar del subtotal
    orden.subtotal_repuestos -= detalle.subtotal

    # Eliminar detalle
    db.delete(detalle)

    # Validar descuento <= subtotal tras eliminar
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tras eliminar, el descuento excede el subtotal. Reduzca el descuento a máximo {float(subtotal_base):.2f}"
        )
    orden.calcular_total()

    db.commit()
    db.refresh(orden)

    logger.info(f"Repuesto eliminado de orden: {orden.numero_orden}")
    return orden

@router.get("/estados/listar")
def listar_estados(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar todos los estados posibles de una orden de trabajo
    """
    estados = [
        {"valor": "PENDIENTE", "nombre": "Pendiente"},
        {"valor": "EN_PROCESO", "nombre": "En Proceso"},
        {"valor": "ESPERANDO_REPUESTOS", "nombre": "Esperando Repuestos"},
        {"valor": "ESPERANDO_AUTORIZACION", "nombre": "Esperando Autorización"},
        {"valor": "COMPLETADA", "nombre": "Completada"},
        {"valor": "ENTREGADA", "nombre": "Entregada"},
        {"valor": "CANCELADA", "nombre": "Cancelada"}
    ]
    return {"estados": estados}

@router.get("/prioridades/listar")
def listar_prioridades(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar todas las prioridades posibles de una orden de trabajo
    """
    prioridades = [
        {"valor": "BAJA", "nombre": "Baja"},
        {"valor": "NORMAL", "nombre": "Normal"},
        {"valor": "ALTA", "nombre": "Alta"},
        {"valor": "URGENTE", "nombre": "Urgente"}
    ]
    return {"prioridades": prioridades}

@router.get("/estadisticas/dashboard")
def obtener_estadisticas_dashboard(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"]))
):
    """
    Obtener estadísticas del dashboard de órdenes de trabajo
    - **ADMIN, CAJA**
    """
    # Contar órdenes por estado
    ordenes_por_estado = db.query(
        OrdenTrabajo.estado,
        func.count(OrdenTrabajo.id).label('total')
    ).group_by(OrdenTrabajo.estado).all()
    
    # Órdenes del día
    hoy = datetime.now().date()
    ordenes_hoy = db.query(func.count(OrdenTrabajo.id)).filter(
        func.date(OrdenTrabajo.fecha_ingreso) == hoy
    ).scalar()
    
    # Total facturado = suma de ventas vinculadas a órdenes (no canceladas)
    # Refleja lo realmente cobrado/facturado, no el total estimado del trabajo
    total_facturado = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.id_orden.isnot(None),
        Venta.estado != "CANCELADA"
    ).scalar() or 0
    
    # Órdenes urgentes pendientes
    ordenes_urgentes = db.query(func.count(OrdenTrabajo.id)).filter(
        OrdenTrabajo.prioridad == "URGENTE",
        OrdenTrabajo.estado.in_(["PENDIENTE", "EN_PROCESO"])
    ).scalar()
    
    return {
        "ordenes_por_estado": [
            {"estado": estado, "total": total} 
            for estado, total in ordenes_por_estado
        ],
        "ordenes_hoy": ordenes_hoy,
        "total_facturado": float(total_facturado),
        "ordenes_urgentes": ordenes_urgentes
    }
