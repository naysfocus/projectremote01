# Upgrade Remote Server v1.6.1 → v1.7

1. Pastikan backup Remote Server valid.
2. Hentikan stack lama dengan `docker compose down` (tanpa `-v`).
3. Gunakan folder `remote-server` dari paket `project-remote-v1.0`.
4. Jalankan `docker compose up -d --build`.
5. Jalankan `docker compose ps` dan pastikan server, scheduler, integrations healthy.
6. Login ke dashboard dan cek Device → Progres Remote HP.

Migration mempertahankan device, lokasi, tag, token, integrasi, laporan dan histori Remote HP yang sudah ada.
