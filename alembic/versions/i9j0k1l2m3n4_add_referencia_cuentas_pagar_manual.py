"""add referencia_factura a cuentas_pagar_manual

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-01-29

Referencia / nº factura para requisitos contables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'i9j0k1l2m3n4'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cuentas_pagar_manual' AND COLUMN_NAME = 'referencia_factura'"
    ))
    if r.fetchone() is None:
        op.add_column('cuentas_pagar_manual', sa.Column('referencia_factura', sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column('cuentas_pagar_manual', 'referencia_factura')
