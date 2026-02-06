"""
Aplicación principal FastAPI - MedinaAutoDiag
Sistema de gestión para taller mecánico
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from contextlib import asynccontextmanager
import logging

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    Limiter = None
    _rate_limit_exceeded_handler = None
    get_remote_address = None
    SlowAPIMiddleware = None
    RateLimitExceeded = None

from app.database import engine, Base
from app.config import settings
from app.logging_config import setup_logging
from app.middleware.logging import LoggingMiddleware
from app.middleware.docs_auth import DocsAuthMiddleware

# Importar routers
from app.routers.usuarios import router as usuarios_router
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

# Rate limiting (opcional: si slowapi no está instalado, se omite)
def _rate_limit_string() -> str:
    r, w = settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW
    if w <= 60:
        return f"{r}/minute"
    if w <= 3600:
        return f"{r}/hour"
    return f"{r}/day"

_limiter = None
if SLOWAPI_AVAILABLE and settings.RATE_LIMIT_ENABLED:
    _limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[_rate_limit_string()],
        enabled=True,
    )

def _exempt_decorator(f):
    """Exenta del rate limit a /, /health, /config cuando slowapi está activo."""
    return _limiter.exempt(f) if _limiter is not None else f


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


# Docs: en debug siempre; en producción si DOCS_ENABLED
_docs_enabled = settings.DEBUG_MODE or settings.DOCS_ENABLED
_docs_protected = _docs_enabled and settings.DOCS_REQUIRE_AUTH and not settings.DEBUG_MODE

# Crear aplicación FastAPI
# openapi_url: coherente con docs (no exponer schema si docs deshabilitados)
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de gestión para taller mecánico",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# Protección de docs con Basic Auth en producción (cuando DOCS_REQUIRE_AUTH)
if _docs_protected:
    app.add_middleware(
        DocsAuthMiddleware,
        require_auth=True,
        docs_user=settings.DOCS_USER,
        docs_password=settings.DOCS_PASSWORD,
    )

# Rate limiting (solo si slowapi está instalado)
if _limiter is not None:
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

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
from app.routers.ventas import router as ventas_router
app.include_router(ventas_router)

# 🧾 CLIENTES
app.include_router(clientes_router, tags=["Clientes"])

# 🚗 VEHÍCULOS
app.include_router(vehiculos_router, tags=["Vehículos"])

# 📋 CATÁLOGO VEHÍCULOS (órdenes de compra, independiente de clientes)
from app.routers.catalogo_vehiculos import router as catalogo_vehiculos_router
app.include_router(catalogo_vehiculos_router)

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
@_exempt_decorator
def root(request: Request):
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
@_exempt_decorator
def health_check(request: Request):
    """
    Health check para monitoreo. Verifica conexión real a la base de datos.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check falló - BD desconectada: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "detail": str(e)},
        )


@app.get("/config", tags=["Root"])
@_exempt_decorator
def get_config(request: Request):
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
