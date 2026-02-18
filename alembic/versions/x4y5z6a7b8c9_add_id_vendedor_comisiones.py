"""add id_vendedor to ventas and ordenes_trabajo

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-02-18

Fase 0 comisiones: permite asociar vendedor a ventas y OT para cálculo de comisiones.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "x4y5z6a7b8c9"
down_revision: Union[str, None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ventas", sa.Column("id_vendedor", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ventas_id_vendedor",
        "ventas",
        "usuarios",
        ["id_vendedor"],
        ["id_usuario"],
    )
    op.create_index("ix_ventas_id_vendedor", "ventas", ["id_vendedor"])

    op.add_column("ordenes_trabajo", sa.Column("id_vendedor", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ordenes_trabajo_id_vendedor",
        "ordenes_trabajo",
        "usuarios",
        ["id_vendedor"],
        ["id_usuario"],
    )
    op.create_index("ix_ordenes_trabajo_id_vendedor", "ordenes_trabajo", ["id_vendedor"])


def downgrade() -> None:
    op.drop_index("ix_ordenes_trabajo_id_vendedor", "ordenes_trabajo")
    op.drop_constraint("fk_ordenes_trabajo_id_vendedor", "ordenes_trabajo", type_="foreignkey")
    op.drop_column("ordenes_trabajo", "id_vendedor")

    op.drop_index("ix_ventas_id_vendedor", "ventas")
    op.drop_constraint("fk_ventas_id_vendedor", "ventas", type_="foreignkey")
    op.drop_column("ventas", "id_vendedor")
