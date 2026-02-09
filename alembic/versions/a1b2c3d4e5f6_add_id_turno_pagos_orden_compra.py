"""add id_turno to pagos_orden_compra

Revision ID: a1b2c3d4e5f6
Revises: 3d82bfb3252b
Create Date: 2026-01-30

Añade id_turno opcional a pagos_orden_compra para vincular pagos en efectivo
a proveedores con el turno de caja (integración Caja - Cuentas por pagar).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3d82bfb3252b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'pagos_orden_compra',
        sa.Column('id_turno', sa.Integer(), sa.ForeignKey('caja_turnos.id_turno'), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('pagos_orden_compra', 'id_turno')
