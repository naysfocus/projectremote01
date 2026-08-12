# Remote Server v1.7

Control plane untuk ekosistem Project Remote. v1.7 melanjutkan v1.6.1 dan menambahkan monitoring **Wireless ADB** serta **Remote HP Android Controller** tanpa mengubah token/device lama.

## Komponen yang dipantau

- Remote HP PC: device, HP, akun, placement, tanggal batch, upload, sesi aktif.
- HP fisik: identitas stabil, USB serial, endpoint Wi-Fi ADB, transport aktif.
- Remote HP Android: paired/online, versi aplikasi, handset tujuan.
- Video Mixer: aktivitas/job output seperti versi sebelumnya.
- Site/lokasi dan zona waktu WIB/WITA/WIT.

## Upgrade

Database tetap memakai volume Docker `scaleup_server_data`. Migration 0007 menambah kolom transport HP secara in-place dan tabel Android Controller baru. Jangan gunakan `docker compose down -v`.

Untuk distribusi terintegrasi, ikuti `README-MULAI-DI-SINI.md` pada root `project-remote-v1.0`.
