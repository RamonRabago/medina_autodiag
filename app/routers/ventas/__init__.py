"""
Módulo de ventas dividido en sub-módulos:
- reportes: estadísticas y reportes
- acciones: vincular orden, cancelar
- ticket: generación de PDF
- crud: listar, obtener, actualizar, crear
"""
from fastapi import APIRouter

from .reportes import router as reportes_router
from .acciones import router as acciones_router
from .ticket import router as ticket_router
from .crud import router as crud_router

router = APIRouter(prefix="/ventas", tags=["Ventas"])

# Orden: rutas más específicas primero
router.include_router(reportes_router)
router.include_router(acciones_router)
router.include_router(ticket_router)
router.include_router(crud_router)
