# Aktivasi dan Sinkronisasi Remote HP v1.50

Remote HP terhubung otomatis ke:

```text
https://remote.darda.uk
```

Tidak perlu mengedit `.env`, JSON, atau alamat server.

## Penggunaan pertama

1. Jalankan setup satu kali.
2. Jalankan Remote HP dan buka `http://localhost:5001`.
3. Buat kode aktivasi **Remote HP** dari Remote Server atau Telegram.
4. Masukkan kode. Kode berlaku satu jam.

Token disimpan pada profil pengguna OS. Restart aplikasi tidak meminta kode baru selama token masih valid.

## Data yang disinkronkan

- HP: ID lokal, nama, label, serial ADB, status online.
- Akun: ID lokal dan username.
- Penempatan akun: HP dan slot Original/Kloning.
- Sesi: akun, HP, tanggal batch, target, jumlah berhasil, status, waktu mulai/selesai.

Tidak disinkronkan:

- password;
- email;
- nomor telepon;
- catatan pribadi;
- caption;
- nama/path/file video.

## Pola sinkronisasi

- Startup dan setiap enam jam: rekonsiliasi lengkap.
- Perubahan HP/akun/placement: snapshot inventaris.
- Progres upload: hanya sesi yang berubah, bukan seluruh histori.
- Internet putus: data tetap tersimpan lokal dan dikirim ulang setelah koneksi pulih.
- Revoke: seluruh API lokal tetap diblokir seperti pada v1.48.

## Upgrade dari v1.48

1. Tutup Remote HP v1.48.
2. Ekstrak v1.50 ke folder baru.
3. Salin `remote_hp.db` dari folder v1.48 ke folder v1.50 **sebelum menjalankan v1.50 pertama kali**.
4. Jalankan `setup-windows.bat` bila diperlukan, lalu `jalankan-windows.bat`.

Token aktivasi berada di profil OS, sehingga umumnya tidak perlu aktivasi ulang.
