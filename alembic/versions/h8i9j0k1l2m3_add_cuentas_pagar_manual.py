"""add cuentas_pagar_manual and pagos_cuenta_pagar_manual

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-01-29

Cuentas por pagar manuales: facturas, renta, servicios sin OC.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Idempotente: MySQL hace commit implícito en DDL, la tabla puede existir si falló antes
    r1 = conn.execute(sa.text("SHOW TABLES LIKE 'cuentas_pagar_manual'"))
    if r1.fetchone() is None:
        op.create_table(
            'cuentas_pagar_manual',
            sa.Column('id_cuenta', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('id_proveedor', sa.Integer(), nullable=True),
            sa.Column('acreedor_nombre', sa.String(150), nullable=True),
            sa.Column('concepto', sa.String(200), nullable=False),
            sa.Column('monto_total', sa.Numeric(10, 2), nullable=False),
            sa.Column('fecha_registro', sa.Date(), server_default=sa.text("(CURDATE())"), nullable=False),
            sa.Column('fecha_vencimiento', sa.Date(), nullable=True),
            sa.Column('observaciones', sa.Text(), nullable=True),
            sa.Column('id_usuario', sa.Integer(), nullable=False),
            sa.Column('cancelada', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('creado_en', sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(['id_proveedor'], ['proveedores.id_proveedor'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario']),
            sa.PrimaryKeyConstraint('id_cuenta'),
        )
        op.create_index('ix_cuentas_pagar_manual_id_cuenta', 'cuentas_pagar_manual', ['id_cuenta'])

    r2 = conn.execute(sa.text("SHOW TABLES LIKE 'pagos_cuenta_pagar_manual'"))
    if r2.fetchone() is None:
        op.create_table(
            'pagos_cuenta_pagar_manual',
            sa.Column('id_pago', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('id_cuenta', sa.Integer(), nullable=False),
            sa.Column('id_usuario', sa.Integer(), nullable=False),
            sa.Column('id_turno', sa.Integer(), nullable=True),
            sa.Column('fecha', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('monto', sa.Numeric(10, 2), nullable=False),
            sa.Column('metodo', sa.String(20), nullable=False),
            sa.Column('referencia', sa.String(100), nullable=True),
            sa.Column('observaciones', sa.String(255), nullable=True),
            sa.ForeignKeyConstraint(['id_cuenta'], ['cuentas_pagar_manual.id_cuenta'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario']),
            sa.ForeignKeyConstraint(['id_turno'], ['caja_turnos.id_turno']),
            sa.PrimaryKeyConstraint('id_pago'),
        )
        op.create_index('ix_pagos_cuenta_pagar_manual_id_pago', 'pagos_cuenta_pagar_manual', ['id_pago'])


def downgrade() -> None:
    op.drop_table('pagos_cuenta_pagar_manual')
    op.drop_table('cuentas_pagar_manual')
