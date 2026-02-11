"""add tabla password_reset_tokens

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-02-10

Tabla para tokens de recuperacion de contrasena.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(sa.text("SHOW TABLES LIKE 'password_reset_tokens'"))
    if r.fetchone() is None:
        op.create_table(
            'password_reset_tokens',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('email', sa.String(100), nullable=False),
            sa.Column('token', sa.String(100), nullable=False),
            sa.Column('expira_en', sa.DateTime(), nullable=False),
            sa.Column('creado_en', sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'])
        op.create_index('ix_password_reset_tokens_email', 'password_reset_tokens', ['email'])
        op.create_index('ix_password_reset_tokens_token', 'password_reset_tokens', ['token'], unique=True)


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
