"""mejoras cotización y orden de trabajo

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-02-16

- fecha_vigencia_cotizacion en ordenes_trabajo
- estado COTIZADA en ordenes_trabajo
- repuesto_id nullable + descripcion_libre en detalles_repuesto_orden (repuestos sin inventario)
- precio_compra_estimado en detalles_repuesto_orden
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'u1v2w3x4y5z6'
down_revision: Union[str, None] = 't0u1v2w3x4y5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Vigencia cotización
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_trabajo' AND COLUMN_NAME = 'fecha_vigencia_cotizacion'"
    ))
    if r.fetchone() is None:
        op.add_column(
            'ordenes_trabajo',
            sa.Column('fecha_vigencia_cotizacion', sa.Date(), nullable=True)
        )

    # 2. Estado COTIZADA
    op.execute("""
        ALTER TABLE ordenes_trabajo MODIFY COLUMN estado
        ENUM('PENDIENTE', 'COTIZADA', 'EN_PROCESO', 'ESPERANDO_REPUESTOS', 'ESPERANDO_AUTORIZACION', 'COMPLETADA', 'ENTREGADA', 'CANCELADA')
        NOT NULL DEFAULT 'PENDIENTE'
    """)

    # 3. detalles_repuesto_orden: repuesto_id nullable, descripcion_libre
    r2 = conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalles_repuesto_orden' AND COLUMN_NAME = 'descripcion_libre'"
    ))
    if r2.fetchone() is None:
        op.add_column(
            'detalles_repuesto_orden',
            sa.Column('descripcion_libre', sa.String(300), nullable=True)
        )
    # Hacer repuesto_id nullable
    op.alter_column(
        'detalles_repuesto_orden',
        'repuesto_id',
        existing_type=sa.Integer(),
        nullable=True
    )

    # 4. precio_compra_estimado
    r3 = conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalles_repuesto_orden' AND COLUMN_NAME = 'precio_compra_estimado'"
    ))
    if r3.fetchone() is None:
        op.add_column(
            'detalles_repuesto_orden',
            sa.Column('precio_compra_estimado', sa.Numeric(10, 2), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('ordenes_trabajo', 'fecha_vigencia_cotizacion')
    op.execute("""
        ALTER TABLE ordenes_trabajo MODIFY COLUMN estado
        ENUM('PENDIENTE', 'EN_PROCESO', 'ESPERANDO_REPUESTOS', 'ESPERANDO_AUTORIZACION', 'COMPLETADA', 'ENTREGADA', 'CANCELADA')
        NOT NULL DEFAULT 'PENDIENTE'
    """)
    op.drop_column('detalles_repuesto_orden', 'descripcion_libre')
    op.drop_column('detalles_repuesto_orden', 'precio_compra_estimado')
    op.alter_column(
        'detalles_repuesto_orden',
        'repuesto_id',
        existing_type=sa.Integer(),
        nullable=False
    )
