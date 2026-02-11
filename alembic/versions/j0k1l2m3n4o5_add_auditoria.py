"""add tabla auditoria

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-01-29

Tabla de auditoría para registrar acciones de usuarios.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'j0k1l2m3n4o5'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(sa.text("SHOW TABLES LIKE 'auditoria'"))
    if r.fetchone() is None:
        op.create_table(
            'auditoria',
            sa.Column('id_auditoria', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('id_usuario', sa.Integer(), nullable=False),
            sa.Column('modulo', sa.String(80), nullable=False),
            sa.Column('accion', sa.String(50), nullable=False),
            sa.Column('id_referencia', sa.Integer(), nullable=True),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('fecha', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario']),
            sa.PrimaryKeyConstraint('id_auditoria'),
        )
        op.create_index('ix_auditoria_id_auditoria', 'auditoria', ['id_auditoria'])


def downgrade() -> None:
    op.drop_table('auditoria')
