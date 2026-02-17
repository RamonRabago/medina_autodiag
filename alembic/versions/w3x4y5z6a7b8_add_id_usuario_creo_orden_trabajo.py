"""add id_usuario_creo to ordenes_trabajo

Revision ID: w3x4y5z6a7b8
Revises: k2l3m4n5o6p7
Create Date: 2026-02-17

Registra quién creó cada orden de trabajo (usuario de recepción/caja).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'w3x4y5z6a7b8'
down_revision: Union[str, None] = 'k2l3m4n5o6p7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ordenes_trabajo',
        sa.Column('id_usuario_creo', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_ordenes_trabajo_usuario_creo',
        'ordenes_trabajo',
        'usuarios',
        ['id_usuario_creo'],
        ['id_usuario'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_ordenes_trabajo_usuario_creo', 'ordenes_trabajo', type_='foreignkey')
    op.drop_column('ordenes_trabajo', 'id_usuario_creo')
