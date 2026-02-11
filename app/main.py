"""
Aplicación principal FastAPI - MedinaAutoDiag
Sistema de gestión para taller mecánico
"""
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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


def _asegurar_columna_diferencia_caja():
    """Añade columna diferencia a caja_turnos si no existe (fallback cuando migraciones no corren)."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE caja_turnos ADD COLUMN diferencia NUMERIC(10, 2) NULL"))
            conn.commit()
            logger.info("✓ Columna caja_turnos.diferencia añadida")
    except Exception as e:
        err_msg = str(e)
        if "1060" in err_msg or "Duplicate column" in err_msg:
            logger.info("Columna caja_turnos.diferencia ya existe")
        else:
            logger.warning(f"Columna diferencia: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de inicio y cierre de la aplicación
    """
    # INICIO
    logger.info("=" * 60)
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    # Crear tablas en la base de datos (en producción se suele usar alembic upgrade head)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tablas de base de datos creadas/verificadas")
    except Exception as e:
        logger.error(f"✗ Error al crear tablas: {str(e)}")
        if settings.DEBUG_MODE:
            raise
        logger.warning("La app arranca sin BD; corrige DATABASE_URL y reinicia.")
    
    # Siempre intentar añadir diferencia (fallback para Railway sin migraciones)
    try:
        _asegurar_columna_diferencia_caja()
    except Exception as e:
        logger.warning(f"Columna diferencia (no crítico): {e}")
    
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
_project_root = Path(__file__).resolve().parent.parent
uploads_path = _project_root / "uploads"
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")
frontend_path = _project_root / "frontend" / "dist"

# Router API bajo prefijo /api (para frontend con baseURL /api)
from fastapi import APIRouter
api_router = APIRouter()

# 🚨 ADMIN ALERTAS
api_router.include_router(admin_alertas_router, prefix="/admin")
# 🔐 AUTENTICACIÓN
api_router.include_router(auth_router)
# 👤 USUARIOS
api_router.include_router(usuarios_router)
# 💰 VENTAS
from app.routers.ventas import router as ventas_router
api_router.include_router(ventas_router)
# 🧾 CLIENTES
api_router.include_router(clientes_router)
# 📅 CITAS
from app.routers.citas import router as citas_router
api_router.include_router(citas_router)
# 🚗 VEHÍCULOS
api_router.include_router(vehiculos_router)
# 📋 CATÁLOGO VEHÍCULOS
from app.routers.catalogo_vehiculos import router as catalogo_vehiculos_router
api_router.include_router(catalogo_vehiculos_router)
if settings.DEBUG_MODE:
    api_router.include_router(test_router)
# 💳 PAGOS
api_router.include_router(pagos.router)
# 💵 CAJA
api_router.include_router(caja.router)
# 💸 GASTOS
from app.routers.gastos import router as gastos_router
api_router.include_router(gastos_router)
# 📥 EXPORTACIONES
api_router.include_router(exportaciones.router)
# INVENTARIO
api_router.include_router(categorias_router)
from app.routers.bodegas import router as bodegas_router
api_router.include_router(bodegas_router)
from app.routers.ubicaciones import router as ubicaciones_router
from app.routers.estantes import router as estantes_router
from app.routers.niveles import router as niveles_router
from app.routers.filas import router as filas_router
api_router.include_router(ubicaciones_router)
api_router.include_router(estantes_router)
api_router.include_router(niveles_router)
api_router.include_router(filas_router)
api_router.include_router(proveedores_router)
from app.routers.ordenes_compra import router as ordenes_compra_router
api_router.include_router(ordenes_compra_router)
from app.routers.cuentas_pagar_manuales import router as cuentas_pagar_manuales_router
api_router.include_router(cuentas_pagar_manuales_router)
api_router.include_router(repuestos_router)
api_router.include_router(movimientos_router)
api_router.include_router(inventario_reportes_router)
from app.routers.devoluciones import router as devoluciones_router
api_router.include_router(devoluciones_router)
from app.routers.auditoria import router as auditoria_router
api_router.include_router(auditoria_router)
# ÓRDENES DE TRABAJO
api_router.include_router(servicios_router)
from app.routers.categorias_servicios import router as categorias_servicios_router
api_router.include_router(categorias_servicios_router)
api_router.include_router(ordenes_trabajo_router)

@api_router.get("/config", tags=["Config"])
@_exempt_decorator
def get_config_api(request: Request):
    """Configuración pública para el frontend (IVA, etc.)"""
    return {"iva_porcentaje": settings.IVA_PORCENTAJE}

app.include_router(api_router, prefix="/api")

# ==========================================
# ENDPOINTS RAÍZ
# ==========================================

@app.get("/", tags=["Root"])
@_exempt_decorator
def root(request: Request):
    """Endpoint raíz: en producción con SPA sirve la app; si no, estado del API."""
    if frontend_path.exists():
        return FileResponse(frontend_path / "index.html")
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


# ==========================================
# SPA FRONTEND (producción)
# ==========================================
frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "dist"
index_path = frontend_path / "index.html"
if frontend_path.exists() and index_path.exists():
    assets_path = frontend_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

    @app.get("/{full_path:path}")
    @_exempt_decorator
    def serve_spa(full_path: str):
        """Sirve el SPA React para rutas no-API."""
        if full_path.startswith("api") or full_path.startswith("uploads") or full_path in ("health", "docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404)
        fp = frontend_path / full_path
        if fp.exists() and fp.is_file():
            return FileResponse(fp)
        return FileResponse(index_path)
else:
    logger.warning("frontend/dist no encontrado o sin index.html. Ejecuta 'cd frontend && npm run build' para servir el SPA desde el backend.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG_MODE
    )
