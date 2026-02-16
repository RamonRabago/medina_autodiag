"""add id_orden_trabajo to ordenes_compra

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-02-16

Vínculo OT ↔ OC: permite ver desde la OT qué OCs se generaron y desde la OC ir a la OT origen.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'v2w3x4y5z6a7'
down_revision: Union[str, None] = 'u1v2w3x4y5z6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ordenes_compra',
        sa.Column('id_orden_trabajo', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_ordenes_compra_id_orden_trabajo',
        'ordenes_compra', 'ordenes_trabajo',
        ['id_orden_trabajo'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_ordenes_compra_id_orden_trabajo', 'ordenes_compra', ['id_orden_trabajo'], unique=False)


def downgrade() -> None:
    op.drop_constraint('fk_ordenes_compra_id_orden_trabajo', 'ordenes_compra', type_='foreignkey')
    op.drop_index('ix_ordenes_compra_id_orden_trabajo', table_name='ordenes_compra')
    op.drop_column('ordenes_compra', 'id_orden_trabajo')
