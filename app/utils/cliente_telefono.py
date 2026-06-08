"""
Utilidades para búsqueda y validación de teléfonos de clientes.
"""
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.utils.validators import validar_telefono_mexico


def normalizar_telefono(telefono: str | None) -> str | None:
    """Normaliza teléfono a solo dígitos. Retorna None si es inválido o vacío."""
    if not telefono or not str(telefono).strip():
        return None
    try:
        return validar_telefono_mexico(str(telefono).strip())
    except ValueError:
        return None


def buscar_cliente_por_telefono(db: Session, telefono: str, excluir_id: int | None = None) -> Cliente | None:
    """
    Busca un cliente por teléfono comparando la versión normalizada (solo dígitos).
    """
    tel_norm = normalizar_telefono(telefono)
    if not tel_norm:
        return None

    query = db.query(Cliente).filter(Cliente.telefono.isnot(None))
    if excluir_id is not None:
        query = query.filter(Cliente.id_cliente != excluir_id)

    for cliente in query.all():
        if normalizar_telefono(cliente.telefono) == tel_norm:
            return cliente
    return None
