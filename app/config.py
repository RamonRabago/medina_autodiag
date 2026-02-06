"""
Configuración centralizada de la aplicación
Todas las variables de entorno y configuraciones están aquí
"""
import os
from dotenv import load_dotenv
from typing import List

# Cargar variables de entorno
load_dotenv()


class Settings:
    """Configuración de la aplicación"""
    
    # Base de datos
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "medina_autodiag")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL de conexión a la base de datos"""
        return (
            f"mysql+pymysql://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:"
            f"{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )
    
    # JWT (en producción debe configurarse explícitamente)
    _SECRET_KEY_DEFAULT: str = "CAMBIA_ESTA_LLAVE_POR_ALGO_LARGO_Y_SEGURO"
    SECRET_KEY: str = os.getenv("SECRET_KEY", _SECRET_KEY_DEFAULT)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    
    # Aplicación
    APP_NAME: str = os.getenv("APP_NAME", "MEDINAAUTODIAG API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # IVA (configurable, p. ej. 8 o 16 según régimen en México)
    IVA_PORCENTAJE: float = float(os.getenv("IVA_PORCENTAJE", "8"))
    IVA_FACTOR: float = 1.0 + (float(os.getenv("IVA_PORCENTAJE", "8")) / 100.0)

    # Documentación OpenAPI (producción)
    # DOCS_ENABLED: exponer /docs y /redoc en producción (default: True)
    DOCS_ENABLED: bool = os.getenv("DOCS_ENABLED", "True").lower() == "true"
    # DOCS_REQUIRE_AUTH: proteger docs con HTTP Basic Auth en producción
    DOCS_REQUIRE_AUTH: bool = os.getenv("DOCS_REQUIRE_AUTH", "True").lower() == "true"
    DOCS_USER: str = os.getenv("DOCS_USER", "admin")
    DOCS_PASSWORD: str = os.getenv("DOCS_PASSWORD", "cambiar_en_produccion")


# Instancia única de configuración
settings = Settings()


def _validate_secret_key() -> None:
    """
    En producción (DEBUG_MODE=False), SECRET_KEY debe configurarse explícitamente.
    No permitir el valor por defecto ni claves cortas.
    """
    if settings.DEBUG_MODE:
        return
    key = settings.SECRET_KEY
    if not key or key == Settings._SECRET_KEY_DEFAULT or len(key) < 32:
        raise RuntimeError(
            "SECRET_KEY no configurado o inseguro en producción. "
            "Configure SECRET_KEY en variables de entorno con al menos 32 caracteres. "
            "Ejemplo: python -c \"import secrets; print(secrets.token_hex(32))\""
        )


_validate_secret_key()
