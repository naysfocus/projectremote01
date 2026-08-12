# Aktivasi Video Mixer v1.22.1

1. Windows: jalankan `run-windows.bat`. Linux: jalankan `./run.sh`. Perintah `docker compose up -d --build` juga dapat digunakan tanpa GPU.
2. Buka `http://localhost:5000`.
3. Di Remote Server buka **Kode Aktivasi** lalu buat kode untuk **Video Mixer**.
4. Masukkan kode pada halaman aktivasi. Kode berlaku 1 jam.
5. Setelah berhasil, dashboard Video Mixer terbuka dan device muncul pada `https://remote.darda.uk`.

Aktivasi tersimpan pada volume Docker `video_matrix_client_data`. Jangan menjalankan `docker compose down -v` karena opsi `-v` menghapus token aktivasi.

## Kontrol akses

- Revoke dari Remote Server memblokir seluruh API lokal dan menghentikan render aktif.
- Reactivate mengizinkan aplikasi digunakan kembali tanpa kode baru.
- Gangguan internet murni memakai grace period 3 jam setelah koneksi sukses terakhir.
- Konflik sesi atau revoke tidak boleh dilewati oleh grace period.
