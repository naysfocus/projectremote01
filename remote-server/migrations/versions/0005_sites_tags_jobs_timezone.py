"""sites, tags, jobs and Indonesia timezone support

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-06 21:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("timezone_name", sa.String(length=80), nullable=False, server_default="Asia/Jakarta"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_sites_name"), "sites", ["name"], unique=False)
    op.create_index(op.f("ix_sites_is_active"), "sites", ["is_active"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=False)

    # SQLite batch table reconstruction would drop and recreate `devices`.
    # Because existing child tables use ON DELETE CASCADE, that can erase
    # historical reports and authorizations. Add the nullable column in-place.
    op.add_column("devices", sa.Column("site_id", sa.Integer(), nullable=True))
    op.create_index("ix_devices_site_id", "devices", ["site_id"], unique=False)

    op.create_table(
        "device_tags",
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id", "tag_id"),
    )

    op.create_table(
        "work_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("app_type", sa.String(length=32), nullable=False),
        sa.Column("client_job_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("planned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("app_type IN ('matrix_generator', 'remote_hp')", name="ck_work_job_app_type"),
        sa.CheckConstraint("status IN ('running', 'completed', 'cancelled', 'failed')", name="ck_work_job_status"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "app_type", "client_job_id", name="uq_work_job_client"),
    )
    op.create_index("ix_work_jobs_device_id", "work_jobs", ["device_id"], unique=False)
    op.create_index("idx_work_jobs_status_updated", "work_jobs", ["status", "updated_at"], unique=False)
    op.create_index("idx_work_jobs_device_started", "work_jobs", ["device_id", "started_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_work_jobs_device_started", table_name="work_jobs")
    op.drop_index("idx_work_jobs_status_updated", table_name="work_jobs")
    op.drop_index("ix_work_jobs_device_id", table_name="work_jobs")
    op.drop_table("work_jobs")
    op.drop_table("device_tags")
    op.drop_index("ix_devices_site_id", table_name="devices")
    with op.batch_alter_table("devices") as batch_op:
        batch_op.drop_column("site_id")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_sites_is_active"), table_name="sites")
    op.drop_index(op.f("ix_sites_name"), table_name="sites")
    op.drop_table("sites")
