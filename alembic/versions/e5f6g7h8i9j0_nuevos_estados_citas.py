"""nuevos estados citas: CONFIRMADA por defecto, SI_ASISTIO, motivo_cancelacion

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-09

Flujo: Crear cita -> CONFIRMADA. Luego: SI_ASISTIO, NO_ASISTIO o CANCELADA (con motivo).
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Añadir columna motivo_cancelacion
    op.execute("ALTER TABLE citas ADD COLUMN motivo_cancelacion TEXT NULL")

    # 2. Convertir estados existentes antes de cambiar el enum
    op.execute("UPDATE citas SET estado = 'CONFIRMADA' WHERE estado = 'PENDIENTE'")
    op.execute("UPDATE citas SET estado = 'SI_ASISTIO' WHERE estado = 'REALIZADA'")

    # 3. Modificar enum: CONFIRMADA, SI_ASISTIO, NO_ASISTIO, CANCELADA
    op.execute("""
        ALTER TABLE citas MODIFY COLUMN estado
        ENUM('CONFIRMADA', 'SI_ASISTIO', 'NO_ASISTIO', 'CANCELADA')
        NOT NULL DEFAULT 'CONFIRMADA'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE citas DROP COLUMN motivo_cancelacion")
    op.execute("""
        ALTER TABLE citas MODIFY COLUMN estado
        ENUM('PENDIENTE', 'CONFIRMADA', 'REALIZADA', 'CANCELADA', 'NO_ASISTIO')
        NOT NULL DEFAULT 'PENDIENTE'
    """)
