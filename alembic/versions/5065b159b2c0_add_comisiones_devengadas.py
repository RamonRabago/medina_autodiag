"""add comisiones_devengadas

Revision ID: 5065b159b2c0
Revises: y5z6a7b8c9d0
Create Date: 2026-02-18 14:02:35.041471

Fase 2 comisiones: tabla para registrar comisiones al pagar venta.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5065b159b2c0"
down_revision: Union[str, None] = "y5z6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tipo_enum = sa.Enum(
        "MANO_OBRA",
        "PARTES",
        "SERVICIOS_VENTA",
        "PRODUCTOS_VENTA",
        name="tipobasecomision_devengada",
    )
    op.create_table(
        "comisiones_devengadas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_venta", sa.Integer(), nullable=False),
        sa.Column("id_detalle", sa.Integer(), nullable=True),
        sa.Column("tipo_base", tipo_enum, nullable=False),
        sa.Column("base_monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("porcentaje", sa.Numeric(5, 2), nullable=False),
        sa.Column("monto_comision", sa.Numeric(10, 2), nullable=False),
        sa.Column("fecha_venta", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id_usuario"]),
        sa.ForeignKeyConstraint(["id_venta"], ["ventas.id_venta"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comisiones_devengadas_id", "comisiones_devengadas", ["id"])
    op.create_index("ix_comisiones_devengadas_id_usuario", "comisiones_devengadas", ["id_usuario"])
    op.create_index("ix_comisiones_devengadas_id_venta", "comisiones_devengadas", ["id_venta"])
    op.create_index("ix_comisiones_devengadas_fecha_venta", "comisiones_devengadas", ["fecha_venta"])


def downgrade() -> None:
    op.drop_index("ix_comisiones_devengadas_fecha_venta", "comisiones_devengadas")
    op.drop_index("ix_comisiones_devengadas_id_venta", "comisiones_devengadas")
    op.drop_index("ix_comisiones_devengadas_id_usuario", "comisiones_devengadas")
    op.drop_index("ix_comisiones_devengadas_id", "comisiones_devengadas")
    op.drop_table("comisiones_devengadas")
