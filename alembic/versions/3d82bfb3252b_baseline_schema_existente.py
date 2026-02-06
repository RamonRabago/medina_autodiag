"""baseline_schema_existente

Revision ID: 3d82bfb3252b
Revises: None (migración inicial)
Create Date: 2026-02-06 08:23:24.426051

Marcar el esquema actual como baseline. No crea ni modifica tablas.
Para BD existente: alembic stamp head
Para BD nueva: iniciar app (create_all), luego alembic stamp head
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d82bfb3252b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
