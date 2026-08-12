# Project Remote v1.0

Paket ini adalah baseline terpadu empat aplikasi Project Remote. Mulai release ini, distribusi dilakukan sebagai satu ZIP utuh agar versi antar-komponen tidak bercabang lagi.

## Komponen

| Folder | Versi komponen | Fungsi |
|---|---:|---|
| `remote-server/` | 1.7 | Control plane VPS: lisensi, device, lokasi, monitoring, inventaris Remote HP, progres, Telegram, Cloudflare |
| `remote-hp-pc/` | 1.50.0 | Engine PC/laptop: ADB USB/Wi-Fi, akun, sesi upload, sinkronisasi server, Mobile API Android |
| `video-mixer/` | 1.22.1 | Mixer/generator video lokal; release dibekukan pada milestone ini |
| `remote-hp-android/` | 1.0.0 | Companion Android: pairing, setup sesi, overlay Bubble/Compact/Expanded, caption clipboard |

## Status release

**Software Final Candidate.** Automated/static validation telah dijalankan untuk source yang dapat diuji di lingkungan build. Sertifikasi fisik tetap dilakukan kemudian dengan PC + HP Android nyata, terutama Wireless ADB, build/install APK, overlay, dan workflow 24/24.

## Urutan deployment saat pengujian fisik

1. Upgrade `remote-server/` ke VPS.
2. Upgrade `remote-hp-pc/` pada PC/laptop dan pertahankan `remote_hp.db` lama sesuai panduan upgrade.
3. `video-mixer/` tetap dapat dijalankan seperti release v1.22.1.
4. Buka `remote-hp-android/` di Android Studio mengikuti `BUILD-APK.md`.
5. Jalankan Remote HP PC dalam LAN mode hanya pada jaringan tepercaya untuk pairing Android.
6. Lakukan certification checklist dari file `CERTIFICATION-CHECKLIST.md`.

## Aturan penting

- Jangan pernah menjalankan `docker compose down -v` pada Remote Server/Video Mixer jika volume perlu dipertahankan.
- Android Controller berbicara ke Remote HP PC melalui LAN; bukan langsung ke VPS.
- Wireless ADB dan Android Controller adalah jalur berbeda: PC→HP untuk ADB, HP→PC untuk Mobile API.
- TikTok tetap dioperasikan manual. Android companion tidak memakai Accessibility Service atau auto-click.
