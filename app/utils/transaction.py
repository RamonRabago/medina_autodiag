"""
Utilidades para manejo de transacciones.
Un solo commit al final, rollback en caso de error.
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session):
    """
    Context manager para operaciones con transacción.
    Hace commit al salir correctamente, rollback en caso de excepción.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
