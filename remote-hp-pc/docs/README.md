# Dokumentasi Remote HP

Dokumentasi dibagi menjadi dua jenis agar keputusan jangka panjang tidak bercampur dengan keadaan versi yang terus berubah.

## Dokumentasi statis

Folder `static/` menyimpan keputusan arsitektur dan aturan produk yang relatif stabil. Dokumen ini hanya berubah ketika arah sistem berubah.

- `static/ARSITEKTUR-TARGET.md` — bentuk akhir PC server dan aplikasi Android.
- `static/KEPUTUSAN-PRODUK.md` — aturan yang sudah disepakati, termasuk pairing perangkat dan 24 post per sesi.

## Dokumentasi dinamis

Folder `dynamic/` menyimpan keadaan implementasi saat ini. Bagian ini diperbarui pada setiap versi.

- `dynamic/STATUS-IMPLEMENTASI.md` — fitur yang sudah tersedia, belum tersedia, dan langkah berikutnya.
- `dynamic/CHANGELOG.md` — perubahan per versi mulai v1.41.
- `dynamic/system-status.json` — ringkasan machine-readable untuk pemeriksaan cepat atau tooling di masa depan.

Dokumen lama di root `docs/` dipertahankan agar tautan dan panduan versi sebelumnya tidak rusak.
