"""
Configuración de la base de datos con SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings

# Aiven y otros proveedores exigen SSL; PyMySQL no siempre aplica ssl-mode=REQUIRED
# desde la URL, así que forzamos SSL cuando la URL lo indica.
_url = settings.DATABASE_URL
_connect_args = {}
if "ssl-mode=REQUIRED" in _url or "ssl_mode=REQUIRED" in _url or "aivencloud.com" in _url:
    _connect_args["ssl"] = True

# Motor de base de datos
engine = create_engine(
    _url,
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
