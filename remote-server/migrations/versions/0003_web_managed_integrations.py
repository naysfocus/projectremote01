"""web managed integration settings

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-04 15:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "integration_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("telegram_token_encrypted", sa.Text(), nullable=True),
        sa.Column("telegram_admin_id", sa.String(length=40), nullable=True),
        sa.Column("telegram_bot_username", sa.String(length=80), nullable=True),
        sa.Column("telegram_pair_code", sa.String(length=12), nullable=True),
        sa.Column("telegram_pair_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cloudflare_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cloudflare_token_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "public_base_url",
            sa.String(length=512),
            nullable=False,
            server_default="http://100.113.142.11:8800",
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_admin_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("integration_config")
