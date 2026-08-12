# API Contract — Remote Server v1.7

Semua timestamp teknis menggunakan ISO 8601 dan disimpan dalam UTC. `batch_date` adalah tanggal operasional yang dipilih di Remote HP dan tidak dikonversi berdasarkan lokasi VPS.

Semua endpoint client selain aktivasi menggunakan:

```http
Authorization: Bearer <access_token>
```

## Aktivasi dan sesi

```text
POST /api/v1/activate
POST /api/v1/session/open
POST /api/v1/session/heartbeat
POST /api/v1/session/close
POST /api/v1/report
```

Grace period hanya berlaku pada kegagalan jaringan. Penolakan eksplisit seperti `revoked`, `session_conflict`, atau `session_superseded` tidak boleh dilewati client.

## Sinkronisasi inventaris Remote HP

### `POST /api/v1/remote-hp/inventory-sync`

Khusus token dengan `app_type=remote_hp`.

```json
{
  "snapshot_id": "inventory-uuid",
  "synced_at": "2026-08-06T14:00:00Z",
  "handsets": [
    {
      "client_device_id": 1,
      "name": "HP Jakarta 01",
      "serial": "ADB-SERIAL",
      "label": "Utama",
      "online": true,
      "created_at": "2026-08-01T00:00:00Z"
    }
  ],
  "accounts": [
    {
      "client_account_id": 10,
      "username": "akun.contoh",
      "created_at": "2026-08-01T00:00:00Z"
    }
  ],
  "placements": [
    {
      "client_placement_id": 100,
      "client_account_id": 10,
      "client_device_id": 1,
      "app_slot": "original",
      "created_at": "2026-08-01T00:00:00Z"
    }
  ]
}
```

Snapshot bersifat authoritative untuk inventaris saat ini. Baris yang tidak lagi ada ditandai tidak aktif, bukan dihapus bersama riwayatnya.

## Sinkronisasi progres upload

### `POST /api/v1/remote-hp/session-sync`

Maksimal 250 sesi per request. Client v1.48 mengirim satu sesi yang berubah untuk progres biasa dan batch penuh saat startup/rekonsiliasi berkala.

```json
{
  "sync_id": "sessions-uuid",
  "synced_at": "2026-08-06T14:05:00Z",
  "sessions": [
    {
      "client_session_id": 501,
      "client_account_id": 10,
      "client_device_id": 1,
      "account_username": "akun.contoh",
      "device_name": "HP Jakarta 01",
      "app_slot": "original",
      "batch_date": "2026-08-06",
      "status": "active",
      "planned_count": 24,
      "completed_count": 8,
      "failed_count": 0,
      "folder_name": "batch-01",
      "started_at": "2026-08-06T13:00:00Z",
      "finished_at": null
    }
  ]
}
```

Status yang valid: `pending`, `active`, `finished`, `cancelled`, `failed`.

### `POST /api/v1/remote-hp/session-reconcile`

Dipakai pada sinkronisasi penuh untuk menandai sesi yang sudah dihapus dari database lokal. Mendukung hingga 250.000 ID sesi.

```json
{
  "reconcile_id": "reconcile-uuid",
  "synced_at": "2026-08-06T14:10:00Z",
  "present_session_ids": [501, 502, 503]
}
```

## Batas data dan privasi

Remote Server tidak memerlukan dan client v1.48 tidak mengirim:

- password akun;
- email atau nomor telepon;
- caption;
- nama file dan path file video;
- isi atau file video.

Data yang diterima hanya metadata operasional untuk monitoring.

## Admin dan operasional

Admin memakai session cookie dan CSRF. Halaman utama yang relevan:

```text
GET /sites
GET /sites/{site_id}
GET /devices/{device_id}
GET /devices/{device_id}/remote-hp
GET /exports/activity.csv
GET /system
```
