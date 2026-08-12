# Status Implementasi

Versi saat ini: **v1.42**  
Tanggal pembaruan: **2026-08-01**

## Sudah tersedia

### Patch Windows v1.42

- Tempel ke HP memakai WinAPI native, bukan PowerShell.
- Error WinError 2 akibat executable PowerShell tidak ditemukan sudah ditutup.
- Fokus scrcpy dan pengiriman Ctrl+V tetap 0 ms tanpa proses eksternal.

### Server/web yang tetap berfungsi

- Workflow upload FIFO melalui ADB.
- scrcpy auto-split dan Tempel ke HP tanpa delay.
- Mode Cepat tiga langkah.
- Caption fallback generate ulang maksimal tiga kali.
- Guard duplikasi berdasarkan nama file dan tanggal batch.
- Histori, dashboard, akun TikTok, dan perangkat.

### Fondasi arah server baru pada v1.41

- Semua sesi baru dipaksa server menjadi tepat 24 video.
- Pilihan policy `4`, `5`, `All`, dan `Manual` dihapus dari UI.
- Request policy dari client lama diterima tetapi diabaikan.
- Record `upload_sessions.policy` tetap disimpan dengan nilai 24 untuk kompatibilitas database.
- Subfolder batch harus memiliki tepat 24 video siap.
- Folder flat lama boleh memiliki lebih dari 24 video; server mengambil 24 pertama per sesi.
- Jadwal sesi baru selalu memiliki 24 slot jam dari 00 sampai 23.
- Panel Jadwal Default disederhanakan menjadi Aturan Jadwal 24 Post.
- Endpoint sumber video dan `/api/settings` mempublikasikan `posts_per_session: 24`; mode jadwal dibaca sebagai `fixed_24`.

## Belum tersedia

- Folder video dinamis 1 sampai N.
- Menu Super Admin untuk membuat, mengubah, dan menonaktifkan folder video.
- Model `video_collections` dan `video_batches` di database.
- Pairing Android dan token perangkat.
- API mobile.
- Aplikasi Android dan overlay.
- ADB serial wajib saat membuat/edit perangkat.
- Sinkronisasi status realtime PC ↔ Android.

## Langkah server berikutnya yang disarankan

1. Tambahkan tabel koleksi dan batch video tanpa menghapus empat folder lama.
2. Tambahkan menu Super Admin **Folder Video**.
3. Buat adapter agar empat folder lama muncul sebagai koleksi legacy.
4. Jadikan ADB serial wajib setelah migrasi data lama aman.
5. Tambahkan pairing perangkat dan API status minimal untuk Android.
