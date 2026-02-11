"""stock y cantidades a DECIMAL - soporte para aceites, litros, etc.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-02-10

Permite decimales en stock (ej: 37.6 L de aceite) y cantidades en movimientos,
ventas, órdenes de compra y órdenes de trabajo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'l2m3n4o5p6q7'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tipo DECIMAL(10,3) para stock y cantidades
QTY_TYPE = sa.Numeric(10, 3)


def upgrade() -> None:
    # Repuestos
    op.alter_column('repuestos', 'stock_actual',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('0'))
    op.alter_column('repuestos', 'stock_minimo',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('5'))
    op.alter_column('repuestos', 'stock_maximo',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('100'))

    # Movimientos de inventario
    op.alter_column('movimientos_inventario', 'cantidad',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False)
    op.alter_column('movimientos_inventario', 'stock_anterior',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False)
    op.alter_column('movimientos_inventario', 'stock_nuevo',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False)

    # Detalle de venta (cantidad de productos)
    op.alter_column('detalle_venta', 'cantidad',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=True,
                    existing_server_default=sa.text('1'))

    # Detalles repuesto orden (órdenes de trabajo)
    op.alter_column('detalles_repuesto_orden', 'cantidad',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('1'))

    # Detalles orden de compra
    op.alter_column('detalles_orden_compra', 'cantidad_solicitada',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False)
    op.alter_column('detalles_orden_compra', 'cantidad_recibida',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('0'))

    # Alertas de inventario
    op.alter_column('alertas_inventario', 'stock_actual',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=True)
    op.alter_column('alertas_inventario', 'stock_minimo',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=True)
    op.alter_column('alertas_inventario', 'stock_maximo',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=True)

    # Cancelación producto (reutilizable/mer)
    op.alter_column('cancelaciones_productos', 'cantidad_reutilizable',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('0'))
    op.alter_column('cancelaciones_productos', 'cantidad_mer',
                    existing_type=sa.Integer(),
                    type_=QTY_TYPE,
                    existing_nullable=False,
                    existing_server_default=sa.text('0'))


def downgrade() -> None:
    INT_TYPE = sa.Integer()

    op.alter_column('cancelaciones_productos', 'cantidad_reutilizable',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('0'))
    op.alter_column('cancelaciones_productos', 'cantidad_mer',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('0'))

    op.alter_column('alertas_inventario', 'stock_actual',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=True)
    op.alter_column('alertas_inventario', 'stock_minimo',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=True)
    op.alter_column('alertas_inventario', 'stock_maximo',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=True)

    op.alter_column('detalles_orden_compra', 'cantidad_solicitada',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=False)
    op.alter_column('detalles_orden_compra', 'cantidad_recibida',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('0'))

    op.alter_column('detalles_repuesto_orden', 'cantidad',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('1'))

    op.alter_column('detalle_venta', 'cantidad',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=True, existing_server_default=sa.text('1'))

    op.alter_column('movimientos_inventario', 'cantidad',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=False)
    op.alter_column('movimientos_inventario', 'stock_anterior',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=False)
    op.alter_column('movimientos_inventario', 'stock_nuevo',
                    existing_type=QTY_TYPE, type_=INT_TYPE, existing_nullable=False)

    op.alter_column('repuestos', 'stock_actual',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('0'))
    op.alter_column('repuestos', 'stock_minimo',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('5'))
    op.alter_column('repuestos', 'stock_maximo',
                    existing_type=QTY_TYPE, type_=INT_TYPE,
                    existing_nullable=False, existing_server_default=sa.text('100'))
