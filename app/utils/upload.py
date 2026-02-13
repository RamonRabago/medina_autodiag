"""
Utilidades para subida de archivos con validación de tamaño.
Evita cargar archivos grandes en memoria antes de rechazarlos (protección OOM).
"""
from fastapi import HTTPException, status

CHUNK_SIZE = 8192


def read_file_with_limit(file, max_bytes: int, max_mb: int) -> bytes:
    """
    Lee el archivo por chunks, rechazando si supera max_bytes.
    Evita agotar memoria con uploads enormes.
    """
    chunks = []
    total = 0
    while True:
        chunk = file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo no debe superar {max_mb} MB"
            )
        chunks.append(chunk)
    return b"".join(chunks)
