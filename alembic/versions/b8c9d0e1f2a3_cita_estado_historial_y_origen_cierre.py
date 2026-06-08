"""cita_estado_historial y estado_origen_cierre en citas

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-08

Fase 1: corrección de estados de citas V2.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE citas
        ADD COLUMN estado_origen_cierre
        ENUM('CONFIRMADA', 'SI_ASISTIO', 'NO_ASISTIO', 'CANCELADA') NULL
        """
    )

    op.create_table(
        "cita_estado_historial",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_cita", sa.Integer(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=20), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=20), nullable=False),
        sa.Column("motivo_codigo", sa.String(length=40), nullable=True),
        sa.Column("motivo_detalle", sa.Text(), nullable=True),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_orden", sa.Integer(), nullable=True),
        sa.Column("origen", sa.String(length=30), nullable=False),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["id_cita"], ["citas.id_cita"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id_usuario"]),
        sa.ForeignKeyConstraint(["id_orden"], ["ordenes_trabajo.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cita_estado_historial_id_cita"),
        "cita_estado_historial",
        ["id_cita"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cita_estado_historial_id"),
        "cita_estado_historial",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cita_estado_historial_id"), table_name="cita_estado_historial")
    op.drop_index(op.f("ix_cita_estado_historial_id_cita"), table_name="cita_estado_historial")
    op.drop_table("cita_estado_historial")
    op.execute("ALTER TABLE citas DROP COLUMN estado_origen_cierre")
