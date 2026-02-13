"""
Servicio seguro para archivos en /uploads.
Permite solo tipos seguros (imágenes, PDFs) y rutas controladas.
Protege contra ejecutables, scripts o XSS si un archivo malicioso llega al disco.
"""
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

# Extensiones permitidas al servir (debe coincidir con subida)
ALLOWED_SERVE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"})

# Subdirectorios permitidos dentro de uploads/
ALLOWED_SUBDIRS = frozenset({"repuestos", "comprobantes"})


def serve_upload_safe(file_path: str, uploads_path: Path) -> FileResponse:
    """
    Sirve un archivo de uploads si pasa validaciones.
    - Sin path traversal (..)
    - Subdirectorio permitido (repuestos, comprobantes)
    - Extensión en whitelist
    - Archivo existe y está dentro del directorio uploads
    """
    # Path traversal
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=404, detail="Not found")

    parts = [p for p in file_path.replace("\\", "/").split("/") if p]
    if not parts:
        raise HTTPException(status_code=404, detail="Not found")

    if parts[0] not in ALLOWED_SUBDIRS:
        raise HTTPException(status_code=404, detail="Not found")

    ext = Path(file_path).suffix.lower()
    if ext not in ALLOWED_SERVE_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Not found")

    full_path = (uploads_path / file_path).resolve()
    base_resolved = uploads_path.resolve()

    if not str(full_path).startswith(str(base_resolved)):
        raise HTTPException(status_code=404, detail="Not found")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    return FileResponse(
        full_path,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=86400",
        },
    )
