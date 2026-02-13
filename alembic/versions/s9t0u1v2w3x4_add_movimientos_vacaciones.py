"""add movimientos_vacaciones (checador fase 5)

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-02-13

Movimientos de vacaciones: TOMA, ACREDITACION, AJUSTE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 's9t0u1v2w3x4'
down_revision: Union[str, None] = 'r8s9t0u1v2w3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'movimientos_vacaciones',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('tipo', sa.Enum('TOMA', 'ACREDITACION', 'AJUSTE', name='tipo_mov_vacaciones'), nullable=False),
        sa.Column('dias', sa.Numeric(5, 2), nullable=False),
        sa.Column('periodo', sa.String(20), nullable=True),
        sa.Column('observaciones', sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_movimientos_vacaciones_id'), 'movimientos_vacaciones', ['id'], unique=False)
    op.create_index('ix_movimientos_vacaciones_id_usuario', 'movimientos_vacaciones', ['id_usuario'], unique=False)
    op.create_index('ix_movimientos_vacaciones_fecha', 'movimientos_vacaciones', ['fecha'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_movimientos_vacaciones_fecha', table_name='movimientos_vacaciones')
    op.drop_index('ix_movimientos_vacaciones_id_usuario', table_name='movimientos_vacaciones')
    op.drop_index(op.f('ix_movimientos_vacaciones_id'), table_name='movimientos_vacaciones')
    op.drop_table('movimientos_vacaciones')
