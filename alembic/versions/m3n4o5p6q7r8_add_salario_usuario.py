"""add salario_base y periodo_pago a usuarios

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-02-10

Etapa 1 Nómina: campos para salario base y periodo de pago por empleado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'm3n4o5p6q7r8'
down_revision: Union[str, None] = 'l2m3n4o5p6q7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('salario_base', sa.Numeric(12, 2), nullable=True))
    op.add_column('usuarios', sa.Column('periodo_pago', sa.Enum('SEMANAL', 'QUINCENAL', 'MENSUAL', name='periodo_pago'), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'periodo_pago')
    op.drop_column('usuarios', 'salario_base')
