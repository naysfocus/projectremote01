"""Remote HP Android controller and wireless ADB monitoring

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-07 22:40:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable columns in-place. Do not reconstruct remote_hp_handsets on
    # SQLite because it already has children with ON DELETE behavior.
    for name, typ in (
        ("stable_uid", sa.String(length=80)),
        ("usb_serial", sa.String(length=255)),
        ("wifi_endpoint", sa.String(length=255)),
        ("preferred_transport", sa.String(length=16)),
        ("active_transport", sa.String(length=16)),
        ("active_serial", sa.String(length=255)),
    ):
        op.add_column("remote_hp_handsets", sa.Column(name, typ, nullable=True))

    op.create_table(
        "remote_hp_mobile_clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_device_id", sa.Integer(), nullable=False),
        sa.Column("client_mobile_id", sa.Integer(), nullable=False),
        sa.Column("handset_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("app_version", sa.String(length=64), nullable=True),
        sa.Column("overlay_contract_version", sa.String(length=32), nullable=True),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["server_device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handset_id"], ["remote_hp_handsets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_device_id", "client_mobile_id", name="uq_remote_hp_mobile_client"),
    )
    op.create_index("ix_remote_hp_mobile_clients_server_device_id", "remote_hp_mobile_clients", ["server_device_id"])
    op.create_index("ix_remote_hp_mobile_clients_handset_id", "remote_hp_mobile_clients", ["handset_id"])
    op.create_index("ix_remote_hp_mobile_clients_status", "remote_hp_mobile_clients", ["status"])
    op.create_index("idx_remote_hp_mobile_server_present", "remote_hp_mobile_clients", ["server_device_id", "is_present"])
    op.create_index("idx_remote_hp_mobile_handset_status", "remote_hp_mobile_clients", ["handset_id", "status"])


def downgrade() -> None:
    op.drop_table("remote_hp_mobile_clients")
    # Downgrade of in-place nullable monitoring columns is intentionally omitted
    # on SQLite production deployments to avoid destructive table rebuilds.
