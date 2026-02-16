"""
Módulo de órdenes de trabajo dividido en sub-módulos:
- catalogos: estados, prioridades, dashboard
- acciones: iniciar, finalizar, entregar, cancelar, autorizar, marcar-cotizacion-enviada
- detalles: agregar/quitar servicios y repuestos
- cotizacion: PDF cotización formal para el cliente
- crud: crear, listar, obtener, actualizar, eliminar
"""
from fastapi import APIRouter

from .catalogos import router as catalogos_router
from .acciones import router as acciones_router
from .detalles import router as detalles_router
from .cotizacion import router as cotizacion_router
from .crud import router as crud_router

router = APIRouter(prefix="/ordenes-trabajo", tags=["Órdenes - Órdenes de Trabajo"])

# Rutas específicas primero (estados/listar, prioridades/listar, estadisticas/dashboard)
router.include_router(catalogos_router)
# Acciones sobre una orden
router.include_router(acciones_router)
# Agregar/quitar servicios y repuestos
router.include_router(detalles_router)
# Cotización PDF (antes de crud para /{id}/cotizacion)
router.include_router(cotizacion_router)
# CRUD principal
router.include_router(crud_router)
