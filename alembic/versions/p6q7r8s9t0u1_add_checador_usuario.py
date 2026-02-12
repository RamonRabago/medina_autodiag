"""add checador campos a usuarios (horas, días, vacaciones, horario)

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-02-10

Checador Fase 1: horas_por_dia, dias_por_semana, dias_vacaciones_saldo,
horario_inicio, horario_fin, dias_semana_trabaja.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'p6q7r8s9t0u1'
down_revision: Union[str, None] = 'o5p6q7r8s9t0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('horas_por_dia', sa.Numeric(4, 2), nullable=True))
    op.add_column('usuarios', sa.Column('dias_por_semana', sa.Integer(), nullable=True))
    op.add_column('usuarios', sa.Column('dias_vacaciones_saldo', sa.Numeric(5, 2), nullable=True))
    op.add_column('usuarios', sa.Column('horario_inicio', sa.String(5), nullable=True))
    op.add_column('usuarios', sa.Column('horario_fin', sa.String(5), nullable=True))
    op.add_column('usuarios', sa.Column('dias_semana_trabaja', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'dias_semana_trabaja')
    op.drop_column('usuarios', 'horario_fin')
    op.drop_column('usuarios', 'horario_inicio')
    op.drop_column('usuarios', 'dias_vacaciones_saldo')
    op.drop_column('usuarios', 'dias_por_semana')
    op.drop_column('usuarios', 'horas_por_dia')
