"""
Configuración de logging para la aplicación
"""
import logging
import sys
from pathlib import Path

# Crear directorio de logs si no existe
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


def setup_logging(debug: bool = False):
    """
    Configura el sistema de logging
    
    Args:
        debug: Si True, muestra logs de nivel DEBUG
    """
    # Nivel de logging
    level = logging.DEBUG if debug else logging.INFO
    
    # Formato de los logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configurar logging básico
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Log a archivo
            logging.FileHandler(
                log_dir / "app.log",
                encoding="utf-8"
            ),
            # Log a consola
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar niveles específicos para librerías
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if debug else logging.WARNING
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Sistema de logging configurado correctamente")
