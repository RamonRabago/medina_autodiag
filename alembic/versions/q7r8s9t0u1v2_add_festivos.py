"""add festivos (checador fase 2)

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-02-13

Catálogo de días festivos. Admin los define manualmente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'q7r8s9t0u1v2'
down_revision: Union[str, None] = 'p6q7r8s9t0u1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'festivos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_festivos_id'), 'festivos', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_festivos_id'), table_name='festivos')
    op.drop_table('festivos')
