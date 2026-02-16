"""add traceabilidad cotizacion enviada

Revision ID: k2l3m4n5o6p7
Revises: v2w3x4y5z6a7
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'k2l3m4n5o6p7'
down_revision = 'v2w3x4y5z6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ordenes_trabajo', sa.Column('fecha_cotizacion_enviada', sa.DateTime(), nullable=True))
    op.add_column('ordenes_trabajo', sa.Column('id_usuario_cotizacion_enviada', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_ordenes_trabajo_usuario_cotizacion_enviada',
        'ordenes_trabajo', 'usuarios',
        ['id_usuario_cotizacion_enviada'], ['id_usuario'],
    )


def downgrade():
    op.drop_constraint('fk_ordenes_trabajo_usuario_cotizacion_enviada', 'ordenes_trabajo', type_='foreignkey')
    op.drop_column('ordenes_trabajo', 'id_usuario_cotizacion_enviada')
    op.drop_column('ordenes_trabajo', 'fecha_cotizacion_enviada')
