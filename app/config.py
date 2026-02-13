"""
Configuración centralizada de la aplicación
Todas las variables de entorno y configuraciones están aquí
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

# Cargar .env desde la raíz del proyecto (independiente del cwd al iniciar)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


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
        """Construye la URL de conexión a la base de datos.
        Si DATABASE_URL está definida en env (p. ej. Railway), se usa esa."""
        url = os.getenv("DATABASE_URL")
        if url:
            # En producción no permitir localhost (Railway debe usar Aiven/PlanetScale)
            if not self.DEBUG_MODE and "localhost" in url:
                raise RuntimeError(
                    "DATABASE_URL apunta a localhost. En producción usa la URI de Aiven/PlanetScale. "
                    "En Railway → Variables → DATABASE_URL: pega la Service URI de Aiven (con ?ssl-mode=REQUIRED). "
                    "No uses variables DB_HOST/DB_USER sueltas; borra esas y deja solo DATABASE_URL con la URI completa."
                )
            # PlanetScale y otros usan mysql://; SQLAlchemy necesita mysql+pymysql://
            if url.startswith("mysql://"):
                url = url.replace("mysql://", "mysql+pymysql://", 1)
            # CRÍTICO: quitar query params (?ssl-mode=REQUIRED etc). PyMySQL falla si llegan al driver.
            if "?" in url:
                url = url.rsplit("?", 1)[0]
            return url
        # Sin DATABASE_URL: en producción obligatorio; en desarrollo usar DB_* o defaults
        if not self.DEBUG_MODE:
            raise RuntimeError(
                "DATABASE_URL no está definida. En Railway → Variables añade DATABASE_URL con la "
                "Service URI de Aiven (Overview → Connection information → Service URI, con ?ssl-mode=REQUIRED)."
            )
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

    # Microsoft Graph API (alternativa a SMTP, evita bloqueos por Security Defaults)
    AZURE_TENANT_ID: str | None = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID: str | None = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET: str | None = os.getenv("AZURE_CLIENT_SECRET")
    AZURE_SEND_AS_EMAIL: str | None = os.getenv("AZURE_SEND_AS_EMAIL")  # Buzón desde el que enviar

    # SMTP para envío de órdenes de compra a proveedores (fallback si Graph no está)
    SMTP_HOST: str | None = os.getenv("SMTP_HOST")  # Si no está, no se envía email
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str | None = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str | None = os.getenv("SMTP_FROM_EMAIL")  # Ej: noreply@taller.com
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # URL pública de la aplicación (para enlaces en emails, ej. recuperación de contraseña)
    APP_PUBLIC_URL: str = os.getenv("APP_PUBLIC_URL", "http://localhost:5173")

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


def _validate_docs_password() -> None:
    """
    En producción con DOCS_REQUIRE_AUTH=True, DOCS_PASSWORD debe configurarse
    explícitamente. No permitir el valor por defecto.
    """
    if settings.DEBUG_MODE:
        return
    if not settings.DOCS_REQUIRE_AUTH or not settings.DOCS_ENABLED:
        return
    if settings.DOCS_PASSWORD in (None, "", "cambiar_en_produccion"):
        raise RuntimeError(
            "DOCS_PASSWORD no configurado en producción. "
            "La documentación está protegida con Basic Auth pero usa una contraseña insegura. "
            "Configure DOCS_PASSWORD en variables de entorno (ej. Railway). "
            "Si no necesita docs protegidos: DOCS_REQUIRE_AUTH=false o DOCS_ENABLED=false"
        )


_validate_secret_key()
_validate_docs_password()
