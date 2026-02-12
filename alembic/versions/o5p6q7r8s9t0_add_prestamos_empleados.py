"""add prestamos_empleados y descuentos_prestamos

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-02-12

Préstamos a empleados: varios por empleado, descuento fijo por periodo.
Si falta, se descuenta igual. Solo ADMIN gestiona.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'o5p6q7r8s9t0'
down_revision: Union[str, None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(sa.text("SHOW TABLES LIKE 'prestamos_empleados'"))
    if r.fetchone() is not None:
        return  # Tablas ya existen (ej. por create_all)
    op.create_table(
        'prestamos_empleados',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('monto_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('descuento_por_periodo', sa.Numeric(10, 2), nullable=False),
        sa.Column('periodo_descuento', sa.Enum('SEMANAL', 'QUINCENAL', 'MENSUAL', name='periodo_descuento_prestamo'), nullable=False),
        sa.Column('fecha_inicio', sa.Date(), nullable=False),
        sa.Column('estado', sa.Enum('ACTIVO', 'LIQUIDADO', 'CANCELADO', name='estado_prestamo'), nullable=False, server_default='ACTIVO'),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        sa.Column('creado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario']),
        sa.ForeignKeyConstraint(['creado_por'], ['usuarios.id_usuario']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_prestamos_empleados_id', 'prestamos_empleados', ['id'])
    op.create_index('ix_prestamos_empleados_id_usuario', 'prestamos_empleados', ['id_usuario'])

    op.create_table(
        'descuentos_prestamos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_prestamo', sa.Integer(), nullable=False),
        sa.Column('monto_descontado', sa.Numeric(10, 2), nullable=False),
        sa.Column('fecha_periodo', sa.Date(), nullable=False),
        sa.Column('creado_en', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['id_prestamo'], ['prestamos_empleados.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_descuentos_prestamos_id', 'descuentos_prestamos', ['id'])
    op.create_index('ix_descuentos_prestamos_id_prestamo', 'descuentos_prestamos', ['id_prestamo'])


def downgrade() -> None:
    op.drop_table('descuentos_prestamos')
    op.drop_table('prestamos_empleados')
