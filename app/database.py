"""
Configuración de la base de datos con SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings

# Motor de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG_MODE,  # Solo mostrar SQL en modo debug
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_recycle=3600,  # Reciclar conexiones cada hora
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
    Dependencia para obtener sesión de base de datos
    Se cierra automáticamente al terminar
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
