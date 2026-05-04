"""add cotizaciones refaccion especial (módulo importación / no local)

Revision ID: a7b8c9d0e1f2
Revises: 5065b159b2c0
Create Date: 2026-05-04

Cotizaciones de refacciones con opciones de compra, comentarios y compras ejecutadas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "5065b159b2c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    r = conn.execute(sa.text("SHOW TABLES LIKE 'cotizaciones_refaccion_especial'"))
    if r.fetchone() is None:
        op.create_table(
            "cotizaciones_refaccion_especial",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("numero", sa.String(50), nullable=False),
            sa.Column("id_cliente", sa.Integer(), nullable=False),
            sa.Column("id_vehiculo", sa.Integer(), nullable=True),
            sa.Column("id_orden_trabajo", sa.Integer(), nullable=True),
            sa.Column("id_usuario_creo", sa.Integer(), nullable=False),
            sa.Column("estado", sa.String(32), nullable=False, server_default="BORRADOR"),
            sa.Column("notas_generales", sa.Text(), nullable=True),
            sa.Column("tc_referencia_usd_mxn", sa.Numeric(12, 4), nullable=True),
            sa.Column("margen_objetivo_pct", sa.Numeric(5, 2), nullable=True),
            sa.Column("congelada", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("id_usuario_aceptacion", sa.Integer(), nullable=True),
            sa.Column("fecha_aceptacion_cliente", sa.DateTime(), nullable=True),
            sa.Column("creado_en", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column(
                "actualizado_en",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["id_cliente"], ["clientes.id_cliente"]),
            sa.ForeignKeyConstraint(["id_vehiculo"], ["vehiculos.id_vehiculo"]),
            sa.ForeignKeyConstraint(["id_orden_trabajo"], ["ordenes_trabajo.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["id_usuario_creo"], ["usuarios.id_usuario"]),
            sa.ForeignKeyConstraint(["id_usuario_aceptacion"], ["usuarios.id_usuario"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_cot_ref_numero", "cotizaciones_refaccion_especial", ["numero"], unique=True)
        op.create_index("ix_cot_ref_cliente", "cotizaciones_refaccion_especial", ["id_cliente"])
        op.create_index("ix_cot_ref_estado", "cotizaciones_refaccion_especial", ["estado"])

    r2 = conn.execute(sa.text("SHOW TABLES LIKE 'lineas_cotizacion_refaccion'"))
    if r2.fetchone() is None:
        op.create_table(
            "lineas_cotizacion_refaccion",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("id_cotizacion", sa.Integer(), nullable=False),
            sa.Column("n_linea", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("descripcion", sa.Text(), nullable=False),
            sa.Column("cantidad", sa.Numeric(10, 3), nullable=False, server_default="1"),
            sa.Column("posicion_lado", sa.String(80), nullable=True),
            sa.Column("observaciones", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["id_cotizacion"],
                ["cotizaciones_refaccion_especial.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_linea_cot_ref_cotizacion", "lineas_cotizacion_refaccion", ["id_cotizacion"])

    r3 = conn.execute(sa.text("SHOW TABLES LIKE 'opciones_compra_linea_cotizacion'"))
    if r3.fetchone() is None:
        op.create_table(
            "opciones_compra_linea_cotizacion",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("id_linea", sa.Integer(), nullable=False),
            sa.Column("origen_nombre", sa.String(160), nullable=False),
            sa.Column("url_compra", sa.String(2048), nullable=True),
            sa.Column("moneda", sa.String(3), nullable=False, server_default="MXN"),
            sa.Column("monto_unitario", sa.Numeric(12, 2), nullable=False),
            sa.Column("tipo_cambio_a_mxn", sa.Numeric(12, 4), nullable=True),
            sa.Column("otros_costos_mxn", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("dias_estimados_entrega", sa.Integer(), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("es_preferida", sa.Boolean(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(
                ["id_linea"],
                ["lineas_cotizacion_refaccion.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_opcion_linea_cot", "opciones_compra_linea_cotizacion", ["id_linea"])

    r4 = conn.execute(sa.text("SHOW TABLES LIKE 'comentarios_cotizacion_refaccion'"))
    if r4.fetchone() is None:
        op.create_table(
            "comentarios_cotizacion_refaccion",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("id_cotizacion", sa.Integer(), nullable=False),
            sa.Column("id_usuario", sa.Integer(), nullable=False),
            sa.Column("mensaje", sa.Text(), nullable=False),
            sa.Column("creado_en", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(
                ["id_cotizacion"],
                ["cotizaciones_refaccion_especial.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id_usuario"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_com_cot_ref_cot", "comentarios_cotizacion_refaccion", ["id_cotizacion"])

    r5 = conn.execute(sa.text("SHOW TABLES LIKE 'compras_ejecutadas_cotizacion_refaccion'"))
    if r5.fetchone() is None:
        op.create_table(
            "compras_ejecutadas_cotizacion_refaccion",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("id_cotizacion", sa.Integer(), nullable=False),
            sa.Column("id_linea", sa.Integer(), nullable=True),
            sa.Column("id_opcion", sa.Integer(), nullable=True),
            sa.Column("monto_pagado", sa.Numeric(12, 2), nullable=False),
            sa.Column("moneda", sa.String(3), nullable=False, server_default="MXN"),
            sa.Column("tipo_cambio_aplicado", sa.Numeric(12, 4), nullable=True),
            sa.Column("metodo", sa.String(20), nullable=False, server_default="OTRO"),
            sa.Column("comprobante_url", sa.String(500), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("fecha_pago", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("id_usuario_registro", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["id_cotizacion"],
                ["cotizaciones_refaccion_especial.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["id_linea"],
                ["lineas_cotizacion_refaccion.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["id_opcion"],
                ["opciones_compra_linea_cotizacion.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(["id_usuario_registro"], ["usuarios.id_usuario"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_compra_ejec_cot", "compras_ejecutadas_cotizacion_refaccion", ["id_cotizacion"])


def downgrade() -> None:
    op.drop_table("compras_ejecutadas_cotizacion_refaccion")
    op.drop_table("comentarios_cotizacion_refaccion")
    op.drop_table("opciones_compra_linea_cotizacion")
    op.drop_table("lineas_cotizacion_refaccion")
    op.drop_table("cotizaciones_refaccion_especial")
