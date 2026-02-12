"""add bono_puntualidad a usuarios

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-02-12

Bono por puntualidad: monto que se suma al cálculo de nómina cuando
el empleado cumple puntualidad en el periodo (Etapa 4).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'n4o5p6q7r8s9'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('bono_puntualidad', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'bono_puntualidad')
