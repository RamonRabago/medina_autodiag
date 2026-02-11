"""
Configuración de la base de datos con SQLAlchemy
"""
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings

_log = logging.getLogger(__name__)

# Aiven y otros proveedores exigen SSL; PyMySQL no siempre aplica ssl-mode=REQUIRED
# desde la URL, así que forzamos SSL cuando la URL lo indica.
_url = settings.DATABASE_URL
_has_database_url = bool(os.getenv("DATABASE_URL"))
# Print siempre visible en Railway (el logging puede no estar configurado aún)
if _has_database_url:
    try:
        part = _url.split("@", 1)[1].split("/")[0].split("?")[0] if "@" in _url else "?"
        print(f"[DB] DATABASE_URL is set. Connection target: {part}", flush=True)
    except Exception:
        print("[DB] DATABASE_URL is set (host not parsed)", flush=True)
else:
    print(f"[DB] DATABASE_URL is NOT set - using DB_HOST={settings.DB_HOST} (set DATABASE_URL in Railway!)", flush=True)
if _has_database_url:
    _log.info("Database: using DATABASE_URL from environment")
    try:
        if "@" in _url:
            part = _url.split("@", 1)[1].split("/")[0].split("?")[0]
            _log.info("Database connection target: %s", part)
    except Exception:
        pass
else:
    _log.warning(
        "Database: using DB_HOST=%s (DATABASE_URL not set - set it in Railway Variables for production)",
        settings.DB_HOST,
    )
_connect_args = {}
if "ssl-mode=REQUIRED" in _url or "ssl_mode=REQUIRED" in _url or "aivencloud.com" in _url:
    # PyMySQL: usar ssl=True (contexto por defecto). NO pasar ssl-mode en la URL:
    # SQLAlchemy la pasa al driver y PyMySQL falla con "unexpected keyword argument 'ssl-mode'"
    _connect_args["ssl"] = True
# Eliminar query params de la URL (ssl-mode, etc.) antes de create_engine
_url_engine = _url.rsplit("?", 1)[0] if "?" in _url else _url

# Motor de base de datos
engine = create_engine(
    _url_engine,
    echo=settings.DEBUG_MODE,  # Solo mostrar SQL en modo debug
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_recycle=3600,  # Reciclar conexiones cada hora
    connect_args=_connect_args,
)

# Sesión de base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para los modelos
Base = declarative_base()


def get_db() -> Session:
    """
    Dependencia para obtener sesión de base de datos.
    Se cierra automáticamente al terminar.
    En caso de excepción se hace rollback antes de cerrar.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
