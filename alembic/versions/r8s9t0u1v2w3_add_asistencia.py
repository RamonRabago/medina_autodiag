"""add asistencia (checador fase 3)

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-02-13

Registro de asistencia día por día por empleado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'r8s9t0u1v2w3'
down_revision: Union[str, None] = 'q7r8s9t0u1v2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'asistencia',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('tipo', sa.Enum(
            'TRABAJO', 'FESTIVO', 'VACACION',
            'PERMISO_CON_GOCE', 'PERMISO_SIN_GOCE',
            'INCAPACIDAD', 'FALTA',
            name='tipo_asistencia'
        ), nullable=False),
        sa.Column('horas_trabajadas', sa.Numeric(4, 2), nullable=True),
        sa.Column('turno_completo', sa.Boolean(), nullable=True),
        sa.Column('aplica_bono_puntualidad', sa.Boolean(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('id_referencia', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_asistencia_id'), 'asistencia', ['id'], unique=False)
    op.create_index('ix_asistencia_id_usuario', 'asistencia', ['id_usuario'], unique=False)
    op.create_index('ix_asistencia_fecha', 'asistencia', ['fecha'], unique=False)
    op.create_index('ix_asistencia_usuario_fecha', 'asistencia', ['id_usuario', 'fecha'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_asistencia_usuario_fecha', table_name='asistencia')
    op.drop_index('ix_asistencia_fecha', table_name='asistencia')
    op.drop_index('ix_asistencia_id_usuario', table_name='asistencia')
    op.drop_index(op.f('ix_asistencia_id'), table_name='asistencia')
    op.drop_table('asistencia')
