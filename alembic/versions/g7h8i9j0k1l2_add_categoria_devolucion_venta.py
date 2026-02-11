"""add categoria DEVOLUCION_VENTA a gastos_operativos

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-01-29

Añade categoría DEVOLUCION_VENTA para registrar devoluciones de dinero
por ventas canceladas como egresos en Gastos.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE gastos_operativos MODIFY COLUMN categoria
        ENUM('RENTA', 'SERVICIOS', 'MATERIAL', 'NOMINA', 'OTROS', 'DEVOLUCION_VENTA')
        NOT NULL DEFAULT 'OTROS'
    """)


def downgrade() -> None:
    # No reversible de forma segura si ya hay registros con DEVOLUCION_VENTA
    pass
