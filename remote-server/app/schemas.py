from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AppType = Literal["matrix_generator", "remote_hp"]


class ActivateRequest(BaseModel):
    code: str = Field(min_length=8, max_length=16)
    app_type: AppType
    fingerprint_hash: str = Field(min_length=32, max_length=128)
    os_type: Literal["linux", "windows"]
    os_info: str = Field(default="", max_length=255)
    app_version: str = Field(default="", max_length=64)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class SessionOpenRequest(BaseModel):
    fingerprint_hash: str = Field(min_length=32, max_length=128)
    app_version: str = Field(default="", max_length=64)


class SessionHeartbeatRequest(BaseModel):
    session_id: str = Field(min_length=16, max_length=64)


class SessionCloseRequest(BaseModel):
    session_id: str = Field(min_length=16, max_length=64)


class ReportItem(BaseModel):
    client_report_id: str = Field(min_length=8, max_length=64)
    event_type: str = Field(min_length=3, max_length=64)
    occurred_at: datetime
    summary: dict[str, Any]


class ReportBatchRequest(BaseModel):
    reports: list[ReportItem] = Field(min_length=1, max_length=50)


class DeviceUpdateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)


class RevokeRequest(BaseModel):
    app_type: AppType


class SuspicionReviewRequest(BaseModel):
    action: Literal["ignored", "revoked"]


class ActivationKeyCreateRequest(BaseModel):
    app_type: AppType
    expires_in_hours: int = Field(default=1, ge=1, le=1)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RemoteHpHandsetSyncItem(BaseModel):
    client_device_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=160)
    serial: str | None = Field(default=None, max_length=255)
    stable_uid: str | None = Field(default=None, max_length=80)
    usb_serial: str | None = Field(default=None, max_length=255)
    wifi_endpoint: str | None = Field(default=None, max_length=255)
    preferred_transport: Literal["auto", "wifi", "usb"] | None = None
    active_transport: Literal["wifi", "usb"] | None = None
    active_serial: str | None = Field(default=None, max_length=255)
    label: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)
    online: bool = False
    created_at: datetime | None = None


class RemoteHpAccountSyncItem(BaseModel):
    client_account_id: int = Field(ge=1)
    username: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    created_at: datetime | None = None


class RemoteHpPlacementSyncItem(BaseModel):
    client_placement_id: int = Field(ge=1)
    client_account_id: int = Field(ge=1)
    client_device_id: int = Field(ge=1)
    app_slot: Literal["original", "kloning"]
    created_at: datetime | None = None




class RemoteHpMobileClientSyncItem(BaseModel):
    client_mobile_id: int = Field(ge=1)
    client_device_id: int = Field(ge=1)
    display_name: str = Field(min_length=1, max_length=160)
    status: Literal["active", "revoked"] = "active"
    app_version: str | None = Field(default=None, max_length=64)
    overlay_contract_version: str | None = Field(default=None, max_length=32)
    paired_at: datetime | None = None
    last_seen_at: datetime | None = None

class RemoteHpInventorySyncRequest(BaseModel):
    snapshot_id: str = Field(min_length=8, max_length=80)
    synced_at: datetime
    handsets: list[RemoteHpHandsetSyncItem] = Field(default_factory=list, max_length=500)
    accounts: list[RemoteHpAccountSyncItem] = Field(default_factory=list, max_length=5000)
    placements: list[RemoteHpPlacementSyncItem] = Field(default_factory=list, max_length=10000)
    mobile_clients: list[RemoteHpMobileClientSyncItem] = Field(default_factory=list, max_length=2000)


class RemoteHpUploadSessionSyncItem(BaseModel):
    client_session_id: int = Field(ge=1)
    client_account_id: int = Field(ge=1)
    client_device_id: int = Field(ge=1)
    account_username: str = Field(min_length=1, max_length=255)
    device_name: str = Field(min_length=1, max_length=160)
    app_slot: Literal["original", "kloning"] | None = None
    batch_date: date | None = None
    status: Literal["pending", "active", "finished", "cancelled", "failed"]
    planned_count: int = Field(default=0, ge=0, le=1000000)
    completed_count: int = Field(default=0, ge=0, le=1000000)
    failed_count: int = Field(default=0, ge=0, le=1000000)
    folder_name: str | None = Field(default=None, max_length=255)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RemoteHpSessionSyncRequest(BaseModel):
    sync_id: str = Field(min_length=8, max_length=80)
    synced_at: datetime
    sessions: list[RemoteHpUploadSessionSyncItem] = Field(min_length=1, max_length=250)


class RemoteHpSessionReconcileRequest(BaseModel):
    reconcile_id: str = Field(min_length=8, max_length=80)
    synced_at: datetime
    present_session_ids: list[int] = Field(default_factory=list, max_length=250000)

    @field_validator("present_session_ids")
    @classmethod
    def validate_session_ids(cls, value: list[int]) -> list[int]:
        if any(item < 1 for item in value):
            raise ValueError("session ids must be positive")
        return list(dict.fromkeys(value))
