"""
Router para Gastos Operativos.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.gasto_operativo import GastoOperativo
from app.models.caja_turno import CajaTurno
from app.schemas.gasto_operativo import GastoOperativoCreate, GastoOperativoUpdate, GastoOperativoOut
from app.services.gastos_service import query_gastos, CATEGORIAS_VALIDAS
from app.utils.roles import require_roles
from app.models.usuario import Usuario
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter(
    prefix="/gastos",
    tags=["Gastos Operativos"],
)


@router.post("/", response_model=GastoOperativoOut, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    data: GastoOperativoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Registra un gasto operativo. Si hay turno abierto, se vincula automáticamente."""
    id_turno = data.id_turno
    if id_turno is None:
        turno = db.query(CajaTurno).filter(
            CajaTurno.id_usuario == current_user.id_usuario,
            CajaTurno.estado == "ABIERTO",
        ).first()
        id_turno = turno.id_turno if turno else None

    gasto = GastoOperativo(
        fecha=data.fecha,
        concepto=data.concepto,
        monto=data.monto,
        categoria=data.categoria,
        id_turno=id_turno,
        id_usuario=current_user.id_usuario,
        observaciones=data.observaciones,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "GASTO", gasto.id_gasto, {"concepto": gasto.concepto, "monto": float(gasto.monto)})
    return gasto


@router.get("/")
def listar_gastos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    fecha_desde: Optional[str] = Query(None, description="YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="YYYY-MM-DD"),
    categoria: Optional[str] = Query(None, description="RENTA, SERVICIOS, MATERIAL, NOMINA, OTROS, DEVOLUCION_VENTA"),
    buscar: Optional[str] = Query(None),
    orden_por: Optional[str] = Query("fecha", description="Ordenar por: fecha, concepto, categoria, monto"),
    direccion: Optional[str] = Query("desc", description="Dirección: asc o desc"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Lista gastos con paginación y filtros."""
    if categoria and categoria.strip().upper() not in CATEGORIAS_VALIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Categoría inválida: '{categoria}'. Use: {', '.join(CATEGORIAS_VALIDAS)}",
        )
    query = query_gastos(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, categoria=categoria, buscar=buscar)

    desc = direccion and str(direccion).lower() == "desc"
    col_map = {
        "fecha": GastoOperativo.fecha,
        "concepto": GastoOperativo.concepto,
        "categoria": GastoOperativo.categoria,
        "monto": GastoOperativo.monto,
    }
    order_col = col_map.get((orden_por or "fecha").lower(), GastoOperativo.fecha)
    query = query.order_by(order_col.desc() if desc else order_col.asc(), GastoOperativo.creado_en.desc())

    total = query.count()
    q_sum = query_gastos(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, categoria=categoria, buscar=buscar)
    total_monto = float(q_sum.with_entities(func.coalesce(func.sum(GastoOperativo.monto), 0)).scalar() or 0)
    gastos = query.offset(skip).limit(limit).all()

    return {
        "gastos": gastos,
        "total": total,
        "total_monto": total_monto,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.get("/resumen")
def resumen_gastos(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Total de gastos en un período (para dashboard y reportes)."""
    query = query_gastos(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    total = query.with_entities(func.coalesce(func.sum(GastoOperativo.monto), 0)).scalar()
    return {"total_gastos": float(total or 0)}


@router.get("/{id_gasto}", response_model=GastoOperativoOut)
def obtener_gasto(
    id_gasto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Obtiene un gasto por ID."""
    gasto = db.query(GastoOperativo).filter(GastoOperativo.id_gasto == id_gasto).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


@router.patch("/{id_gasto}", response_model=GastoOperativoOut)
def actualizar_gasto(
    id_gasto: int,
    data: GastoOperativoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Actualiza un gasto."""
    gasto = db.query(GastoOperativo).filter(GastoOperativo.id_gasto == id_gasto).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(gasto, k, v)
    db.commit()
    db.refresh(gasto)
    registrar_auditoria(db, current_user.id_usuario, "ACTUALIZAR", "GASTO", id_gasto, {"campos": list(update.keys())})
    return gasto


@router.delete("/{id_gasto}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_gasto(
    id_gasto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Elimina un gasto."""
    gasto = db.query(GastoOperativo).filter(GastoOperativo.id_gasto == id_gasto).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    concepto = gasto.concepto
    monto = float(gasto.monto)
    db.delete(gasto)
    db.commit()
    registrar_auditoria(db, current_user.id_usuario, "ELIMINAR", "GASTO", id_gasto, {"concepto": concepto, "monto": monto})