from __future__ import annotations

import re
from sqlalchemy import select

from app.models import Device, Site, WorkJob


def login(client):
    response = client.post("/login", data={"username":"admin","password":"testing-password-123"}, follow_redirects=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def test_site_create_assign_and_dashboard(client, app, activated):
    csrf = login(client)
    created = client.post("/sites", data={"name":"Jakarta Barat","code":"JKT-B","timezone_name":"Asia/Jakarta","notes":"Lokasi uji","csrf_token":csrf}, follow_redirects=False)
    assert created.status_code == 303
    with app.state.database.session_factory() as db:
        site = db.scalar(select(Site).where(Site.code == "JKT-B")); assert site
        device = db.get(Device, activated["device_id"]); assert device
        site_id = site.id
    edited = client.post(f"/devices/{activated['device_id']}/edit", data={"label":"PC JKT 01","notes":"","site_id":str(site_id),"tags":"Shift Malam, PC Render","csrf_token":csrf}, follow_redirects=False)
    assert edited.status_code == 303
    page = client.get("/dashboard")
    assert "Jakarta Barat" in page.text and "PC Render" in page.text and "Video Mixer" in page.text


def test_remote_hp_started_and_cancelled_reports_are_accepted(client, app):
    from datetime import timedelta
    from app.models import ActivationKey
    from app.utils import utcnow
    with app.state.database.session_factory() as db:
        db.add(ActivationKey(code="RH7K-QP2R", app_type="remote_hp", status="pending", expires_at=utcnow()+timedelta(hours=1))); db.commit()
    act=client.post('/api/v1/activate', json={"code":"RH7K-QP2R","app_type":"remote_hp","fingerprint_hash":"b"*64,"os_type":"windows","os_info":"Windows","app_version":"1.47"}).json()
    headers={"Authorization":f"Bearer {act['access_token']}"}
    started={"client_report_id":"rh-start-1","event_type":"upload_session_started","occurred_at":"2026-08-06T20:00:00+07:00","summary":{"local_session_id":12,"account_username":"akun","device_name":"HP 1","video_count":24,"batch_date":"2026-08-06","status":"active"}}
    cancelled={"client_report_id":"rh-cancel-1","event_type":"upload_session_cancelled","occurred_at":"2026-08-06T20:10:00+07:00","summary":{"local_session_id":12,"account_username":"akun","device_name":"HP 1","video_count":5,"batch_date":"2026-08-06","status":"cancelled"}}
    assert client.post('/api/v1/report',headers=headers,json={"reports":[started]}).status_code==200
    assert client.post('/api/v1/report',headers=headers,json={"reports":[cancelled]}).status_code==200
    with app.state.database.session_factory() as db:
        job=db.scalar(select(WorkJob).where(WorkJob.client_job_id=='12')); assert job and job.status=='cancelled' and job.completed_count==5


def test_operation_totals_by_site(client, app, activated):
    import re
    from app.models import ActivityReport, Device, Site
    from app.services.admin import stats_summary
    from app.utils import utcnow
    csrf = login(client)
    client.post('/sites', data={'name':'Bandung','code':'BDG','timezone_name':'Asia/Jakarta','notes':'','csrf_token':csrf})
    with app.state.database.session_factory() as db:
        site = db.scalar(select(Site).where(Site.code == 'BDG'))
        device = db.get(Device, activated['device_id'])
        device.site_id = site.id
        now = utcnow()
        db.add(ActivityReport(device_id=device.id, app_type='matrix_generator', event_type='generate_completed', occurred_at=now, received_at=now, summary_json='{"mode":"classic","video_count":30000,"duration_seconds":1,"run_tag":"today"}', client_report_id='today-mixer'))
        db.add(ActivityReport(device_id=device.id, app_type='remote_hp', event_type='upload_session_completed', occurred_at=now, received_at=now, summary_json='{"account_username":"akun","video_count":24,"batch_date":"2026-08-06","status":"finished"}', client_report_id='today-upload'))
        db.commit()
        summary = stats_summary(db, app.state.settings, site_id=site.id)
        assert summary['generated_videos_today'] == 30000
        assert summary['uploaded_videos_today'] == 24
        assert summary['upload_sessions_today'] == 1
        assert summary['mixer_jobs_today'] == 1


def test_indonesia_timezone_display():
    from datetime import datetime, timezone
    from app.utils import local_display
    value = datetime(2026, 8, 6, 13, 0, tzinfo=timezone.utc)
    assert local_display(value, 'Asia/Jakarta').endswith('20:00 WIB')
    assert local_display(value, 'Asia/Makassar').endswith('21:00 WITA')
    assert local_display(value, 'Asia/Jayapura').endswith('22:00 WIT')
