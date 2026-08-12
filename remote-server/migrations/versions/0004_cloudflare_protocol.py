"""cloudflare protocol and v1.5 defaults

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-04 16:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("integration_config") as batch_op:
        batch_op.add_column(
            sa.Column("cloudflare_protocol", sa.String(length=16), nullable=False, server_default="auto")
        )


def downgrade() -> None:
    with op.batch_alter_table("integration_config") as batch_op:
        batch_op.drop_column("cloudflare_protocol")
