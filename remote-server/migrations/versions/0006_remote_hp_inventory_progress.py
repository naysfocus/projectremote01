"""Remote HP inventory, account placement, and upload progress mirror

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-06 21:48:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "remote_hp_handsets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_device_id", sa.Integer(), nullable=False),
        sa.Column("client_device_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("serial", sa.String(length=255), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("local_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["server_device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_device_id", "client_device_id", name="uq_remote_hp_handset_client"),
    )
    op.create_index("ix_remote_hp_handsets_server_device_id", "remote_hp_handsets", ["server_device_id"])
    op.create_index("ix_remote_hp_handsets_is_online", "remote_hp_handsets", ["is_online"])
    op.create_index("idx_remote_hp_handsets_server_present", "remote_hp_handsets", ["server_device_id", "is_present"])

    op.create_table(
        "remote_hp_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_device_id", sa.Integer(), nullable=False),
        sa.Column("client_account_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("local_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["server_device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_device_id", "client_account_id", name="uq_remote_hp_account_client"),
    )
    op.create_index("ix_remote_hp_accounts_server_device_id", "remote_hp_accounts", ["server_device_id"])
    op.create_index("idx_remote_hp_accounts_server_present", "remote_hp_accounts", ["server_device_id", "is_present"])
    op.create_index("idx_remote_hp_accounts_username", "remote_hp_accounts", ["server_device_id", "username"])

    op.create_table(
        "remote_hp_placements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_device_id", sa.Integer(), nullable=False),
        sa.Column("client_placement_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("handset_id", sa.Integer(), nullable=False),
        sa.Column("app_slot", sa.String(length=16), nullable=False, server_default="original"),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("local_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("app_slot IN ('original', 'kloning')", name="ck_remote_hp_placement_slot"),
        sa.ForeignKeyConstraint(["server_device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["remote_hp_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handset_id"], ["remote_hp_handsets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_device_id", "client_placement_id", name="uq_remote_hp_placement_client"),
        sa.UniqueConstraint("account_id", "handset_id", name="uq_remote_hp_account_handset"),
    )
    op.create_index("ix_remote_hp_placements_server_device_id", "remote_hp_placements", ["server_device_id"])
    op.create_index("ix_remote_hp_placements_account_id", "remote_hp_placements", ["account_id"])
    op.create_index("ix_remote_hp_placements_handset_id", "remote_hp_placements", ["handset_id"])
    op.create_index("idx_remote_hp_placements_server_present", "remote_hp_placements", ["server_device_id", "is_present"])

    op.create_table(
        "remote_hp_upload_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_device_id", sa.Integer(), nullable=False),
        sa.Column("client_session_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("handset_id", sa.Integer(), nullable=False),
        sa.Column("app_slot", sa.String(length=16), nullable=True),
        sa.Column("batch_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("planned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("folder_name", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["server_device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["remote_hp_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["handset_id"], ["remote_hp_handsets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_device_id", "client_session_id", name="uq_remote_hp_upload_session_client"),
    )
    op.create_index("ix_remote_hp_upload_sessions_server_device_id", "remote_hp_upload_sessions", ["server_device_id"])
    op.create_index("ix_remote_hp_upload_sessions_account_id", "remote_hp_upload_sessions", ["account_id"])
    op.create_index("ix_remote_hp_upload_sessions_handset_id", "remote_hp_upload_sessions", ["handset_id"])
    op.create_index("ix_remote_hp_upload_sessions_batch_date", "remote_hp_upload_sessions", ["batch_date"])
    op.create_index("ix_remote_hp_upload_sessions_status", "remote_hp_upload_sessions", ["status"])
    op.create_index("ix_remote_hp_upload_sessions_is_present", "remote_hp_upload_sessions", ["is_present"])
    op.create_index("idx_remote_hp_sessions_device_batch", "remote_hp_upload_sessions", ["server_device_id", "batch_date"])
    op.create_index("idx_remote_hp_sessions_account_batch", "remote_hp_upload_sessions", ["account_id", "batch_date"])
    op.create_index("idx_remote_hp_sessions_status_sync", "remote_hp_upload_sessions", ["status", "last_synced_at"])


def downgrade() -> None:
    op.drop_table("remote_hp_upload_sessions")
    op.drop_table("remote_hp_placements")
    op.drop_table("remote_hp_accounts")
    op.drop_table("remote_hp_handsets")
