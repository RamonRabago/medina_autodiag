"""
Middleware para proteger documentación OpenAPI con HTTP Basic Auth.
Solo aplica cuando DOCS_REQUIRE_AUTH está activo (típicamente en producción).
"""
import base64
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, PlainTextResponse

logger = logging.getLogger(__name__)


def _check_basic_auth(auth_header: str | None, expected_user: str, expected_password: str) -> bool:
    """Verifica credenciales HTTP Basic Auth."""
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        encoded = auth_header[6:]
        decoded = base64.b64decode(encoded).decode("utf-8")
        user, _, password = decoded.partition(":")
        return user == expected_user and password == expected_password
    except Exception:
        return False


def _is_docs_path(path: str) -> bool:
    """Indica si la ruta es de documentación."""
    return (
        path == "/docs"
        or path.startswith("/docs/")
        or path == "/redoc"
        or path.startswith("/redoc/")
        or path == "/openapi.json"
    )


class DocsAuthMiddleware(BaseHTTPMiddleware):
    """
    Protege /docs, /redoc y /openapi.json con HTTP Basic Auth
    cuando DOCS_REQUIRE_AUTH está activo.
    """

    def __init__(self, app, require_auth: bool, docs_user: str, docs_password: str):
        super().__init__(app)
        self.require_auth = require_auth
        self.docs_user = docs_user
        self.docs_password = docs_password

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.require_auth and _is_docs_path(request.url.path):
            auth = request.headers.get("Authorization")
            if not _check_basic_auth(auth, self.docs_user, self.docs_password):
                return PlainTextResponse(
                    "Documentación protegida. Use HTTP Basic Auth.",
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic realm=\"API Docs\""},
                )
        return await call_next(request)
