"""add id_orden to citas

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-09

Añade columna id_orden (FK a ordenes_trabajo, nullable) a la tabla citas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'citas',
        sa.Column('id_orden', sa.Integer(), sa.ForeignKey('ordenes_trabajo.id'), nullable=True)
    )
    op.create_index(op.f('ix_citas_id_orden'), 'citas', ['id_orden'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_citas_id_orden'), table_name='citas')
    op.drop_column('citas', 'id_orden')
