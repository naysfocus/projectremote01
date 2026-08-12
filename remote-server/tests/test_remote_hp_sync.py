from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy import select

from app.models import (
    ActivationKey,
    RemoteHpAccount,
    RemoteHpHandset,
    RemoteHpMobileClient,
    RemoteHpPlacement,
    RemoteHpUploadSession,
    WorkJob,
)
from app.utils import utcnow


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def activate_remote_hp(client, app):
    with app.state.database.session_factory() as db:
        db.add(
            ActivationKey(
                code="RH48-QP2R",
                app_type="remote_hp",
                status="pending",
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        db.commit()
    response = client.post(
        "/api/v1/activate",
        json={
            "code": "RH48-QP2R",
            "app_type": "remote_hp",
            "fingerprint_hash": "b" * 64,
            "os_type": "windows",
            "os_info": "Windows 11",
            "app_version": "1.48.0",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def login(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testing-password-123"},
        follow_redirects=True,
    )
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match


def inventory_payload():
    return {
        "snapshot_id": "inventory-test-0001",
        "synced_at": "2026-08-06T14:45:00Z",
        "handsets": [
            {"client_device_id": 1, "name": "HP Jakarta 01", "serial": "192.168.1.20:37123", "stable_uid": "stable-hp-001", "usb_serial": "SERIAL-1", "wifi_endpoint": "192.168.1.20:37123", "preferred_transport": "auto", "active_transport": "wifi", "active_serial": "192.168.1.20:37123", "label": "Utama", "online": True, "created_at": "2026-08-01T00:00:00Z"},
            {"client_device_id": 2, "name": "HP Jakarta 02", "serial": "SERIAL-2", "online": False, "created_at": "2026-08-01T00:00:00Z"},
        ],
        "accounts": [
            {"client_account_id": 10, "username": "akun.a", "created_at": "2026-08-01T00:00:00Z"},
            {"client_account_id": 11, "username": "akun.b", "created_at": "2026-08-01T00:00:00Z"},
        ],
        "placements": [
            {"client_placement_id": 100, "client_account_id": 10, "client_device_id": 1, "app_slot": "original", "created_at": "2026-08-01T00:00:00Z"},
            {"client_placement_id": 101, "client_account_id": 10, "client_device_id": 2, "app_slot": "kloning", "created_at": "2026-08-01T00:00:00Z"},
            {"client_placement_id": 102, "client_account_id": 11, "client_device_id": 1, "app_slot": "kloning", "created_at": "2026-08-01T00:00:00Z"},
        ],
        "mobile_clients": [
            {"client_mobile_id": 900, "client_device_id": 1, "display_name": "Android Operator 01", "status": "active", "app_version": "1.0.0", "overlay_contract_version": "1.0", "paired_at": "2026-08-07T13:00:00Z", "last_seen_at": "2026-08-07T15:00:00Z"}
        ],
    }


def test_inventory_and_session_reconciliation(client, app):
    activated = activate_remote_hp(client, app)
    headers = auth_header(activated["access_token"])
    inventory = client.post("/api/v1/remote-hp/inventory-sync", headers=headers, json=inventory_payload())
    assert inventory.status_code == 200, inventory.text
    assert inventory.json()["handsets"] == 2
    assert inventory.json()["accounts"] == 2
    assert inventory.json()["placements"] == 3
    assert inventory.json()["mobile_clients"] == 1

    sessions = client.post(
        "/api/v1/remote-hp/session-sync",
        headers=headers,
        json={
            "sync_id": "sessions-test-0001",
            "synced_at": "2026-08-06T14:50:00Z",
            "sessions": [
                {
                    "client_session_id": 501,
                    "client_account_id": 10,
                    "client_device_id": 1,
                    "account_username": "akun.a",
                    "device_name": "HP Jakarta 01",
                    "app_slot": "original",
                    "batch_date": "2026-08-06",
                    "status": "active",
                    "planned_count": 24,
                    "completed_count": 8,
                    "failed_count": 0,
                    "folder_name": "1",
                    "started_at": "2026-08-06T13:00:00Z",
                },
                {
                    "client_session_id": 502,
                    "client_account_id": 11,
                    "client_device_id": 1,
                    "account_username": "akun.b",
                    "device_name": "HP Jakarta 01",
                    "app_slot": "kloning",
                    "batch_date": "2026-08-05",
                    "status": "finished",
                    "planned_count": 24,
                    "completed_count": 24,
                    "failed_count": 0,
                    "folder_name": "2",
                    "started_at": "2026-08-05T13:00:00Z",
                    "finished_at": "2026-08-05T13:45:00Z",
                },
            ],
        },
    )
    assert sessions.status_code == 200, sessions.text
    assert sessions.json() == {
        "ok": True,
        "sync_id": "sessions-test-0001",
        "accepted": 2,
        "created": 2,
        "updated": 0,
    }

    with app.state.database.session_factory() as db:
        assert len(db.scalars(select(RemoteHpHandset)).all()) == 2
        assert len(db.scalars(select(RemoteHpAccount)).all()) == 2
        assert len(db.scalars(select(RemoteHpPlacement)).all()) == 3
        mobile = db.scalar(select(RemoteHpMobileClient))
        assert mobile is not None and mobile.display_name == "Android Operator 01"
        handset = db.scalar(select(RemoteHpHandset).where(RemoteHpHandset.client_device_id == 1))
        assert handset is not None and handset.active_transport == "wifi" and handset.usb_serial == "SERIAL-1"
        rows = db.scalars(select(RemoteHpUploadSession)).all()
        assert len(rows) == 2
        active = next(row for row in rows if row.client_session_id == 501)
        assert active.completed_count == 8
        job = db.scalar(select(WorkJob).where(WorkJob.client_job_id == "501"))
        assert job is not None and job.status == "running" and job.progress_percent == 33

    login(client)
    page = client.get(f"/devices/{activated['device_id']}/remote-hp?batch_date=2026-08-06")
    assert page.status_code == 200, page.text
    assert "HP Jakarta 01" in page.text
    assert "Android Operator 01" in page.text
    assert "WIFI" in page.text
    assert "@akun.a" in page.text
    assert "8 / 24" in page.text
    assert "@akun.b" in page.text
    assert "Belum upload" in page.text


def test_inventory_snapshot_marks_removed_rows_without_deleting_history(client, app):
    activated = activate_remote_hp(client, app)
    headers = auth_header(activated["access_token"])
    assert client.post("/api/v1/remote-hp/inventory-sync", headers=headers, json=inventory_payload()).status_code == 200
    session_payload = {
        "sync_id": "sessions-preserve-1",
        "synced_at": "2026-08-06T14:50:00Z",
        "sessions": [{
            "client_session_id": 700,
            "client_account_id": 11,
            "client_device_id": 2,
            "account_username": "akun.b",
            "device_name": "HP Jakarta 02",
            "app_slot": "original",
            "batch_date": "2026-08-06",
            "status": "finished",
            "planned_count": 24,
            "completed_count": 24,
            "failed_count": 0,
        }],
    }
    assert client.post("/api/v1/remote-hp/session-sync", headers=headers, json=session_payload).status_code == 200
    reduced = inventory_payload()
    reduced["snapshot_id"] = "inventory-test-0002"
    reduced["handsets"] = reduced["handsets"][:1]
    reduced["accounts"] = reduced["accounts"][:1]
    reduced["placements"] = reduced["placements"][:1]
    assert client.post("/api/v1/remote-hp/inventory-sync", headers=headers, json=reduced).status_code == 200
    with app.state.database.session_factory() as db:
        removed_hp = db.scalar(select(RemoteHpHandset).where(RemoteHpHandset.client_device_id == 2))
        removed_account = db.scalar(select(RemoteHpAccount).where(RemoteHpAccount.client_account_id == 11))
        assert removed_hp is not None and removed_hp.is_present is False
        assert removed_account is not None and removed_account.is_present is False
        assert db.scalar(select(RemoteHpUploadSession).where(RemoteHpUploadSession.client_session_id == 700)) is not None


def test_matrix_token_cannot_use_remote_hp_sync(client, activated):
    response = client.post(
        "/api/v1/remote-hp/inventory-sync",
        headers=auth_header(activated["access_token"]),
        json={"snapshot_id": "inventory-wrong-app", "synced_at": "2026-08-06T14:45:00Z", "handsets": [], "accounts": [], "placements": []},
    )
    assert response.status_code == 403
    assert response.json()["status"] == "wrong_app_type"


def test_session_reconcile_hides_deleted_local_history_and_cancels_active_job(client, app):
    activated = activate_remote_hp(client, app)
    headers = auth_header(activated["access_token"])
    assert client.post("/api/v1/remote-hp/inventory-sync", headers=headers, json=inventory_payload()).status_code == 200
    payload = {
        "sync_id": "sessions-reconcile-1",
        "synced_at": "2026-08-06T14:50:00Z",
        "sessions": [
            {
                "client_session_id": 801,
                "client_account_id": 10,
                "client_device_id": 1,
                "account_username": "akun.a",
                "device_name": "HP Jakarta 01",
                "app_slot": "original",
                "batch_date": "2026-08-06",
                "status": "finished",
                "planned_count": 24,
                "completed_count": 24,
                "failed_count": 0,
            },
            {
                "client_session_id": 802,
                "client_account_id": 11,
                "client_device_id": 1,
                "account_username": "akun.b",
                "device_name": "HP Jakarta 01",
                "app_slot": "kloning",
                "batch_date": "2026-08-07",
                "status": "active",
                "planned_count": 24,
                "completed_count": 9,
                "failed_count": 0,
            },
        ],
    }
    assert client.post("/api/v1/remote-hp/session-sync", headers=headers, json=payload).status_code == 200

    reconcile = client.post(
        "/api/v1/remote-hp/session-reconcile",
        headers=headers,
        json={
            "reconcile_id": "reconcile-test-0001",
            "synced_at": "2026-08-06T15:00:00Z",
            "present_session_ids": [801],
        },
    )
    assert reconcile.status_code == 200, reconcile.text
    assert reconcile.json() == {
        "ok": True,
        "reconcile_id": "reconcile-test-0001",
        "present": 1,
        "hidden": 1,
        "restored": 0,
    }

    with app.state.database.session_factory() as db:
        kept = db.scalar(select(RemoteHpUploadSession).where(RemoteHpUploadSession.client_session_id == 801))
        hidden = db.scalar(select(RemoteHpUploadSession).where(RemoteHpUploadSession.client_session_id == 802))
        job = db.scalar(select(WorkJob).where(WorkJob.client_job_id == "802"))
        assert kept is not None and kept.is_present is True
        assert hidden is not None and hidden.is_present is False
        assert job is not None and job.status == "cancelled"

    login(client)
    page = client.get(f"/devices/{activated['device_id']}/remote-hp?batch_date=2026-08-06")
    assert page.status_code == 200, page.text
    assert "2026-08-06" in page.text
    assert "24 / 24" in page.text
    assert "2026-08-07" not in page.text


def test_session_reconcile_accepts_empty_database(client, app):
    activated = activate_remote_hp(client, app)
    response = client.post(
        "/api/v1/remote-hp/session-reconcile",
        headers=auth_header(activated["access_token"]),
        json={
            "reconcile_id": "reconcile-empty-0001",
            "synced_at": "2026-08-06T15:00:00Z",
            "present_session_ids": [],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["present"] == 0
