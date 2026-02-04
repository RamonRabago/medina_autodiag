"""
Aplicación principal FastAPI - MedinaAutoDiag
Sistema de gestión para taller mecánico
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.database import engine, Base
from app.config import settings
from app.logging_config import setup_logging
from app.middleware.logging import LoggingMiddleware

# Importar routers
from app.routers.usuarios import router as usuarios_router
from app.routers.ventas import router as ventas_router
from app.routers.clientes import router as clientes_router
from app.routers.vehiculos import router as vehiculos_router
from app.routers.auth import router as auth_router
from app.routers.test import router as test_router
from app.routers.admin_alertas import router as admin_alertas_router
from app.routers import pagos
from app.routers import caja
from app.routers import exportaciones

# Routers de Inventario
from app.routers.categorias_repuestos import router as categorias_router
from app.routers.proveedores import router as proveedores_router
from app.routers.repuestos import router as repuestos_router
from app.routers.movimientos_inventario import router as movimientos_router
from app.routers.inventario_reportes import router as inventario_reportes_router

# Routers de Órdenes de Trabajo
from app.routers.servicios import router as servicios_router
from app.routers.ordenes_trabajo import router as ordenes_trabajo_router

# Configurar logging
setup_logging(debug=settings.DEBUG_MODE)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de inicio y cierre de la aplicación
    """
    # INICIO
    logger.info("=" * 60)
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    # Crear tablas en la base de datos
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tablas de base de datos creadas/verificadas")
    except Exception as e:
        logger.error(f"✗ Error al crear tablas: {str(e)}")
        raise
    
    yield
    
    # CIERRE
    logger.info("Cerrando aplicación...")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de gestión para taller mecánico",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG_MODE else None,  # Docs solo en debug
    redoc_url="/redoc" if settings.DEBUG_MODE else None,
)


# ==========================================
# MIDDLEWARE
# ==========================================

# CORS - Permitir peticiones desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging de peticiones
app.add_middleware(LoggingMiddleware)

# Archivos estáticos (imágenes subidas)
uploads_path = Path(__file__).resolve().parent.parent / "uploads"
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


# ==========================================
# ROUTERS
# ==========================================

# 🚨 ADMIN ALERTAS
app.include_router(
    admin_alertas_router,
    prefix="/admin",
    tags=["Admin Alertas"]
)

# 🔐 AUTENTICACIÓN
app.include_router(auth_router, tags=["Auth"])

# 👤 USUARIOS
app.include_router(usuarios_router, tags=["Usuarios"])

# 💰 VENTAS
app.include_router(ventas_router, tags=["Ventas"])

# 🧾 CLIENTES
app.include_router(clientes_router, tags=["Clientes"])

# 🚗 VEHÍCULOS
app.include_router(vehiculos_router, tags=["Vehículos"])

# 🧪 TEST (solo en modo debug)
if settings.DEBUG_MODE:
    app.include_router(test_router, tags=["Test"])

# 💳 PAGOS
app.include_router(pagos.router, tags=["Pagos"])

# 💵 CAJA
app.include_router(caja.router, tags=["Caja"])

# 💸 GASTOS OPERATIVOS
from app.routers.gastos import router as gastos_router
app.include_router(gastos_router)

# 📥 EXPORTACIONES
app.include_router(exportaciones.router, tags=["Exportaciones"])

# ==========================================
# INVENTARIO
# ==========================================

# 📦 CATEGORÍAS DE REPUESTOS
app.include_router(categorias_router)

# 🏪 BODEGAS
from app.routers.bodegas import router as bodegas_router
app.include_router(bodegas_router)

# 📍 UBICACIONES
from app.routers.ubicaciones import router as ubicaciones_router
from app.routers.estantes import router as estantes_router
from app.routers.niveles import router as niveles_router
from app.routers.filas import router as filas_router

app.include_router(ubicaciones_router)
app.include_router(estantes_router)
app.include_router(niveles_router)
app.include_router(filas_router)

# 📦 ESTANTES, NIVELES, FILAS
from app.routers.estantes import router as estantes_router
from app.routers.niveles import router as niveles_router
from app.routers.filas import router as filas_router
app.include_router(estantes_router)
app.include_router(niveles_router)
app.include_router(filas_router)

# 🏢 PROVEEDORES
app.include_router(proveedores_router)

# 📋 ÓRDENES DE COMPRA
from app.routers.ordenes_compra import router as ordenes_compra_router
app.include_router(ordenes_compra_router)

# 🔧 REPUESTOS
app.include_router(repuestos_router)

# 📊 MOVIMIENTOS DE INVENTARIO
app.include_router(movimientos_router)

# 📈 REPORTES Y ALERTAS DE INVENTARIO
app.include_router(inventario_reportes_router)


# ==========================================
# ÓRDENES DE TRABAJO
# ==========================================

# 🛠️ SERVICIOS
app.include_router(servicios_router)

# 📂 CATEGORÍAS DE SERVICIOS
from app.routers.categorias_servicios import router as categorias_servicios_router
app.include_router(categorias_servicios_router)

# 📋 ÓRDENES DE TRABAJO
app.include_router(ordenes_trabajo_router)


# ==========================================
# ENDPOINTS RAÍZ
# ==========================================

@app.get("/", tags=["Root"])
def root():
    """
    Endpoint raíz - Verificación de estado del API
    """
    return {
        "status": "online",
        "message": "API conectada correctamente",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Root"])
def health_check():
    """
    Health check para monitoreo
    """
    return {
        "status": "healthy",
        "database": "connected",
    }


@app.get("/config", tags=["Root"])
def get_config():
    """
    Configuración pública (IVA, etc.) para uso del frontend.
    """
    return {
        "iva_porcentaje": settings.IVA_PORCENTAJE,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG_MODE
    )
