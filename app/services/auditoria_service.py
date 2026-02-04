"""
Servicio de auditoría: registra acciones de usuarios sobre módulos.
Si existe tabla de auditoría, persiste; si no, no-op para no bloquear el arranque.
"""
from sqlalchemy.orm import Session
from typing import Any, Optional


def registrar(
    db: Session,
    id_usuario: int,
    accion: str,
    modulo: str,
    id_referencia: Optional[int] = None,
    datos: Optional[dict] = None,
) -> None:
    """
    Registra un evento de auditoría (crear, actualizar, cancelar, etc.).
    Por ahora no-op si no existe tabla auditoria; evita ModuleNotFoundError al cargar ordenes_compra.
    """
    try:
        from app.models.auditoria import Auditoria
        reg = Auditoria(
            id_usuario=id_usuario,
            modulo=modulo,
            accion=accion,
            id_referencia=id_referencia,
            descripcion=str(datos) if datos else None,
        )
        db.add(reg)
        db.commit()
    except Exception:
        # Sin tabla Auditoria o cualquier error: no bloquear la operación
        db.rollback()
        pass
