# Restore Backup

Restore bukan kegiatan rutin. Lakukan hanya saat database bermasalah atau ketika sengaja mengembalikan kondisi lama.

## 1. Lihat nama backup

```bash
docker compose exec server sh -c 'ls -lh /data/backups'
```

## 2. Hentikan server dan scheduler

```bash
docker compose down
```

## 3. Restore backup

Ganti nama file contoh dengan backup yang dipilih:

```bash
docker compose run --rm server python -m app.maintenance restore /data/backups/remote-server-YYYYMMDDTHHMMSSZ.sqlite3
```

Sistem membuat salinan database sebelum restore sebagai pengaman.

## 4. Jalankan kembali

```bash
docker compose up -d
```

## 5. Periksa

```bash
docker compose ps
docker compose logs --tail=100 server
```
