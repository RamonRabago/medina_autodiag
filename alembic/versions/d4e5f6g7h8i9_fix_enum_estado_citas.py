"""fix enum estado citas

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-09

Asegura que la columna estado de citas acepte todos los valores del enum:
PENDIENTE, CONFIRMADA, REALIZADA, CANCELADA, NO_ASISTIO.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE citas MODIFY COLUMN estado
        ENUM('PENDIENTE', 'CONFIRMADA', 'REALIZADA', 'CANCELADA', 'NO_ASISTIO')
        NOT NULL DEFAULT 'PENDIENTE'
    """)


def downgrade() -> None:
    pass  # No reversible de forma segura
