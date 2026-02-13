"""add checa_entrada_salida a usuarios

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-02-13

Empleados que no usan reloj checador: registro manual por Admin.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 't0u1v2w3x4y5'
down_revision: Union[str, None] = 's9t0u1v2w3x4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'usuarios',
        sa.Column('checa_entrada_salida', sa.Boolean(), nullable=True, server_default='1'),
    )


def downgrade() -> None:
    op.drop_column('usuarios', 'checa_entrada_salida')
