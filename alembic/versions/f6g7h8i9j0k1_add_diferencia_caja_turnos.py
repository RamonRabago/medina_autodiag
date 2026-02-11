"""add diferencia to caja_turnos

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-01-29

Añade columna diferencia (monto_cierre - efectivo_esperado) para registrar
faltantes o sobrantes al cerrar turno.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'caja_turnos',
        sa.Column('diferencia', sa.Numeric(10, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('caja_turnos', 'diferencia')
