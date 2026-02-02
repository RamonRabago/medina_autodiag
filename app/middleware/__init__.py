"""
Middleware personalizado de la aplicación
"""
from app.middleware.logging import LoggingMiddleware

__all__ = ["LoggingMiddleware"]
