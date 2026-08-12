from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


device_tags = Table(
    "device_tags",
    Base.metadata,
    Column("device_id", ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(40), unique=True)
    timezone_name: Mapped[str] = mapped_column(String(80), default="Asia/Jakarta", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    devices: Mapped[list[Device]] = relationship(back_populates="site")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    devices: Mapped[list[Device]] = relationship(secondary=device_tags, back_populates="tags")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(160))
    os_type: Mapped[str | None] = mapped_column(String(20))
    os_info: Mapped[str | None] = mapped_column(String(255))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), index=True)

    site: Mapped[Site | None] = relationship(back_populates="devices")
    tags: Mapped[list[Tag]] = relationship(secondary=device_tags, back_populates="devices")
    authorizations: Mapped[list[AppAuthorization]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    reports: Mapped[list[ActivityReport]] = relationship(back_populates="device", cascade="all, delete-orphan")
    remote_hp_handsets: Mapped[list[RemoteHpHandset]] = relationship(
        back_populates="server_device", cascade="all, delete-orphan"
    )
    remote_hp_accounts: Mapped[list[RemoteHpAccount]] = relationship(
        back_populates="server_device", cascade="all, delete-orphan"
    )
    remote_hp_upload_sessions: Mapped[list[RemoteHpUploadSession]] = relationship(
        back_populates="server_device", cascade="all, delete-orphan"
    )
    remote_hp_mobile_clients: Mapped[list[RemoteHpMobileClient]] = relationship(
        back_populates="server_device", cascade="all, delete-orphan"
    )


class AppAuthorization(Base):
    __tablename__ = "app_authorizations"
    __table_args__ = (
        CheckConstraint("app_type IN ('matrix_generator', 'remote_hp')", name="ck_auth_app_type"),
        CheckConstraint("status IN ('active', 'revoked')", name="ck_auth_status"),
        UniqueConstraint("device_id", "app_type", name="uq_device_app"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    app_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    app_version: Mapped[str | None] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    session_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session_ip: Mapped[str | None] = mapped_column(String(64))

    device: Mapped[Device] = relationship(back_populates="authorizations")


class ActivationKey(Base):
    __tablename__ = "activation_keys"
    __table_args__ = (
        CheckConstraint("app_type IN ('matrix_generator', 'remote_hp')", name="ck_key_app_type"),
        CheckConstraint(
            "status IN ('pending', 'consumed', 'expired', 'cancelled')", name="ck_key_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    app_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    created_by_telegram_id: Mapped[str | None] = mapped_column(String(40))
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_by_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))


class Heartbeat(Base):
    __tablename__ = "heartbeats"
    __table_args__ = (Index("idx_heartbeat_device_app_time", "device_id", "app_type", "received_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    app_type: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ActivityReport(Base):
    __tablename__ = "activity_reports"
    __table_args__ = (
        CheckConstraint("app_type IN ('matrix_generator', 'remote_hp')", name="ck_report_app_type"),
        UniqueConstraint("device_id", "client_report_id", name="uq_device_report_id"),
        Index("idx_reports_device_time", "device_id", "occurred_at"),
        Index("idx_reports_app_type_event", "app_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    app_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    client_report_id: Mapped[str] = mapped_column(String(64), nullable=False)

    device: Mapped[Device] = relationship(back_populates="reports")


class WorkJob(Base):
    __tablename__ = "work_jobs"
    __table_args__ = (
        CheckConstraint("app_type IN ('matrix_generator', 'remote_hp')", name="ck_work_job_app_type"),
        CheckConstraint("status IN ('running', 'completed', 'cancelled', 'failed')", name="ck_work_job_status"),
        UniqueConstraint("device_id", "app_type", "client_job_id", name="uq_work_job_client"),
        Index("idx_work_jobs_status_updated", "status", "updated_at"),
        Index("idx_work_jobs_device_started", "device_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    app_type: Mapped[str] = mapped_column(String(32), nullable=False)
    client_job_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    planned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship()


class RemoteHpHandset(Base):
    __tablename__ = "remote_hp_handsets"
    __table_args__ = (
        UniqueConstraint("server_device_id", "client_device_id", name="uq_remote_hp_handset_client"),
        Index("idx_remote_hp_handsets_server_present", "server_device_id", "is_present"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_device_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    serial: Mapped[str | None] = mapped_column(String(255))
    stable_uid: Mapped[str | None] = mapped_column(String(80))
    usb_serial: Mapped[str | None] = mapped_column(String(255))
    wifi_endpoint: Mapped[str | None] = mapped_column(String(255))
    preferred_transport: Mapped[str | None] = mapped_column(String(16))
    active_transport: Mapped[str | None] = mapped_column(String(16))
    active_serial: Mapped[str | None] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    is_present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    local_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    server_device: Mapped[Device] = relationship(back_populates="remote_hp_handsets")
    placements: Mapped[list[RemoteHpPlacement]] = relationship(back_populates="handset")
    upload_sessions: Mapped[list[RemoteHpUploadSession]] = relationship(back_populates="handset")
    mobile_clients: Mapped[list[RemoteHpMobileClient]] = relationship(back_populates="handset")


class RemoteHpMobileClient(Base):
    __tablename__ = "remote_hp_mobile_clients"
    __table_args__ = (
        UniqueConstraint("server_device_id", "client_mobile_id", name="uq_remote_hp_mobile_client"),
        Index("idx_remote_hp_mobile_server_present", "server_device_id", "is_present"),
        Index("idx_remote_hp_mobile_handset_status", "handset_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    client_mobile_id: Mapped[int] = mapped_column(Integer, nullable=False)
    handset_id: Mapped[int] = mapped_column(ForeignKey("remote_hp_handsets.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    app_version: Mapped[str | None] = mapped_column(String(64))
    overlay_contract_version: Mapped[str | None] = mapped_column(String(32))
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    server_device: Mapped[Device] = relationship(back_populates="remote_hp_mobile_clients")
    handset: Mapped[RemoteHpHandset] = relationship(back_populates="mobile_clients")


class RemoteHpAccount(Base):
    __tablename__ = "remote_hp_accounts"
    __table_args__ = (
        UniqueConstraint("server_device_id", "client_account_id", name="uq_remote_hp_account_client"),
        Index("idx_remote_hp_accounts_server_present", "server_device_id", "is_present"),
        Index("idx_remote_hp_accounts_username", "server_device_id", "username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    local_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    server_device: Mapped[Device] = relationship(back_populates="remote_hp_accounts")
    placements: Mapped[list[RemoteHpPlacement]] = relationship(back_populates="account")
    upload_sessions: Mapped[list[RemoteHpUploadSession]] = relationship(back_populates="account")


class RemoteHpPlacement(Base):
    __tablename__ = "remote_hp_placements"
    __table_args__ = (
        UniqueConstraint("server_device_id", "client_placement_id", name="uq_remote_hp_placement_client"),
        UniqueConstraint("account_id", "handset_id", name="uq_remote_hp_account_handset"),
        CheckConstraint("app_slot IN ('original', 'kloning')", name="ck_remote_hp_placement_slot"),
        Index("idx_remote_hp_placements_server_present", "server_device_id", "is_present"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_placement_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("remote_hp_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    handset_id: Mapped[int] = mapped_column(
        ForeignKey("remote_hp_handsets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_slot: Mapped[str] = mapped_column(String(16), default="original", nullable=False)
    is_present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    local_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    account: Mapped[RemoteHpAccount] = relationship(back_populates="placements")
    handset: Mapped[RemoteHpHandset] = relationship(back_populates="placements")


class RemoteHpUploadSession(Base):
    __tablename__ = "remote_hp_upload_sessions"
    __table_args__ = (
        UniqueConstraint("server_device_id", "client_session_id", name="uq_remote_hp_upload_session_client"),
        Index("idx_remote_hp_sessions_device_batch", "server_device_id", "batch_date"),
        Index("idx_remote_hp_sessions_account_batch", "account_id", "batch_date"),
        Index("idx_remote_hp_sessions_status_sync", "status", "last_synced_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("remote_hp_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    handset_id: Mapped[int] = mapped_column(
        ForeignKey("remote_hp_handsets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    app_slot: Mapped[str | None] = mapped_column(String(16))
    batch_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False, index=True)
    is_present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    planned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    folder_name: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    server_device: Mapped[Device] = relationship(back_populates="remote_hp_upload_sessions")
    account: Mapped[RemoteHpAccount] = relationship(back_populates="upload_sessions")
    handset: Mapped[RemoteHpHandset] = relationship(back_populates="upload_sessions")


class SuspicionEvent(Base):
    __tablename__ = "suspicion_events"
    __table_args__ = (
        CheckConstraint("admin_action IS NULL OR admin_action IN ('ignored', 'revoked')", name="ck_suspicion_action"),
        Index("idx_suspicion_device_time", "device_id", "detected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    app_type: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    existing_session_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_request_ip: Mapped[str | None] = mapped_column(String(64))
    admin_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    admin_action: Mapped[str | None] = mapped_column(String(16))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))


class AdminTelegramUser(Base):
    __tablename__ = "admin_telegram_users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'viewer')", name="ck_telegram_role"),)

    telegram_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    telegram_username: Mapped[str | None] = mapped_column(String(80))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="admin", nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (Index("idx_outbox_pending", "sent_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("idx_audit_created", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telegram_token_encrypted: Mapped[str | None] = mapped_column(Text)
    telegram_admin_id: Mapped[str | None] = mapped_column(String(40))
    telegram_bot_username: Mapped[str | None] = mapped_column(String(80))
    telegram_pair_code: Mapped[str | None] = mapped_column(String(12))
    telegram_pair_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cloudflare_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cloudflare_token_encrypted: Mapped[str | None] = mapped_column(Text)
    cloudflare_protocol: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)
    public_base_url: Mapped[str] = mapped_column(String(512), default="http://100.113.142.11:8800", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
