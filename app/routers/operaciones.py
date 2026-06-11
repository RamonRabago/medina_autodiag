"""Router Capa Operativa Central A0 — solo lectura."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.operaciones_schema import OperacionesResumenOut
from app.services.operaciones_service import construir_resumen_operativo
from app.utils.dependencies import get_current_active_user

router = APIRouter(prefix="/operaciones", tags=["Operaciones"])


@router.get("/resumen", response_model=OperacionesResumenOut)
def obtener_resumen_operativo(
    limit_items: int = Query(15, ge=1, le=50),
    incluir_items: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    """
    Resumen operativo consolidado para bandejas P3–P6.
    Solo lectura; mutaciones delegadas a routers existentes.
    """
    return construir_resumen_operativo(
        db,
        current_user,
        limit_items=limit_items,
        incluir_items=incluir_items,
    )
