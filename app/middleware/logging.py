"""
Middleware de logging para registrar todas las peticiones
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que registra información de cada petición HTTP
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesa cada petición y registra información
        """
        # Tiempo de inicio
        start_time = time.time()
        
        # Información de la petición
        method = request.method
        url = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        # Log de entrada
        logger.info(f"→ {method} {url} from {client_host}")
        
        try:
            # Procesar petición
            response = await call_next(request)
            
            # Tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Log de salida
            status_code = response.status_code
            logger.info(
                f"← {method} {url} - Status: {status_code} - "
                f"Time: {process_time:.3f}s"
            )
            
            # Agregar header con tiempo de procesamiento
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log de error
            process_time = time.time() - start_time
            logger.error(
                f"✗ {method} {url} - Error: {str(e)} - "
                f"Time: {process_time:.3f}s"
            )
            raise
