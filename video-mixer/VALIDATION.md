# Validasi Video Mixer v1.22.1

Validasi rilis ini mencakup:

- Nama tampilan aplikasi, halaman aktivasi, script launcher, image, dan container berubah menjadi **Video Mixer**.
- ID internal Remote Server tetap `matrix_generator`; fingerprint dan volume `video_matrix_client_data` dipertahankan untuk kompatibilitas aktivasi lama.
- Default jumlah output tetap **Tanpa limit** dan tidak ada batas maksimum permanen.
- Backend menghitung ulang jumlah output dan meminta konfirmasi bila total melebihi 30.000 video.
- Token konfirmasi terikat pada konfigurasi; perubahan grid, mode, limit, audio, profil output, atau file sumber membatalkan konfirmasi lama.
- Batch limit tepat 30.000 dapat berjalan tanpa popup peringatan.
- Popup menampilkan total output, ambang peringatan, ukuran grid, dan rincian output per mode.
- Browser mengirim zona waktu, offset UTC, waktu lokal, serta run tag lokal; protokol Remote Server tetap menggunakan UTC.
- Label Track/Clip dan empat mode kombinasi tetap konsisten.
- JavaScript lolos pemeriksaan sintaks dan seluruh source Python berhasil dikompilasi.
- 13 pengujian non-Flask lulus: output safety, cross-platform compose, laporan job, aktivasi, grace period, revoke, dan antrean laporan.
- Import aplikasi dan alur endpoint peringatan/konfirmasi diverifikasi dengan harness Flask minimal.
- Manifest SHA-256 dibuat dan diverifikasi sebelum ZIP dirilis.

Pengujian render FFmpeg/GPU dan startup Docker aktual tetap perlu dijalankan pada komputer target dengan video sumber dan encoder target.
