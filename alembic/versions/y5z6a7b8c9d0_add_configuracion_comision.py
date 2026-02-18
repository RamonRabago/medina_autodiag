"""add configuracion_comision table

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-02-18

Fase 0 comisiones: tabla para definir % de comisión por empleado y tipo de base.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "y5z6a7b8c9d0"
down_revision: Union[str, None] = "x4y5z6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tipo_base_enum = sa.Enum(
        "MANO_OBRA",
        "PARTES",
        "SERVICIOS_VENTA",
        "PRODUCTOS_VENTA",
        name="tipobasecomision",
    )
    op.create_table(
        "configuracion_comision",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("tipo_base", tipo_base_enum, nullable=False),
        sa.Column("porcentaje", sa.Numeric(5, 2), nullable=False),
        sa.Column("vigencia_desde", sa.Date(), nullable=False),
        sa.Column("vigencia_hasta", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id_usuario"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_configuracion_comision_id", "configuracion_comision", ["id"])
    op.create_index("ix_configuracion_comision_id_usuario", "configuracion_comision", ["id_usuario"])


def downgrade() -> None:
    op.drop_index("ix_configuracion_comision_id_usuario", "configuracion_comision")
    op.drop_index("ix_configuracion_comision_id", "configuracion_comision")
    op.drop_table("configuracion_comision")
