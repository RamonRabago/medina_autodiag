"""Endpoints de acciones sobre ventas: vincular orden, cancelar."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.ventas_service import VentasService
from app.utils.roles import require_roles

router = APIRouter()


def _valor_err_a_http(e: ValueError) -> HTTPException:
    msg = str(e).lower()
    if "no encontrad" in msg:
        return HTTPException(status_code=404, detail=str(e))
    return HTTPException(status_code=400, detail=str(e))


class VincularOrdenBody(BaseModel):
    id_orden: int | None = None


@router.get("/ordenes-disponibles")
def ordenes_disponibles_para_vincular(
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA")),
):
    """Órdenes ENTREGADAS o COMPLETADAS que aún no tienen venta vinculada."""
    return VentasService.ordenes_disponibles_para_vincular(db, limit=limit)


@router.put("/{id_venta}/vincular-orden")
def vincular_orden_venta(
    id_venta: int,
    body: VincularOrdenBody,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA")),
):
    try:
        return VentasService.vincular_orden_venta(
            db, id_venta, body.id_orden, current_user.id_usuario
        )
    except ValueError as e:
        raise _valor_err_a_http(e)


class ProductoCancelacionItem(BaseModel):
    id_detalle: int
    cantidad_reutilizable: int = Field(0, ge=0)
    cantidad_mer: int = Field(0, ge=0)
    motivo_mer: str | None = None


class CancelarVentaBody(BaseModel):
    motivo: str = Field(..., min_length=5)
    categoria_motivo: str | None = None
    productos: list[ProductoCancelacionItem] | None = None


@router.post("/{id_venta}/cancelar")
def cancelar_venta(
    id_venta: int,
    body: CancelarVentaBody,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    productos_dict = None
    if body.productos:
        productos_dict = [
            {
                "id_detalle": p.id_detalle,
                "cantidad_reutilizable": p.cantidad_reutilizable,
                "cantidad_mer": p.cantidad_mer,
                "motivo_mer": p.motivo_mer,
            }
            for p in body.productos
        ]
    try:
        return VentasService.cancelar_venta(
            db,
            id_venta,
            body.motivo.strip(),
            current_user.id_usuario,
            productos=productos_dict,
        )
    except ValueError as e:
        raise _valor_err_a_http(e)
