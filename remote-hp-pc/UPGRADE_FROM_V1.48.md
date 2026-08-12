# Upgrade Remote HP v1.48 ke v1.50

v1.50 adalah upgrade struktur koneksi ADB. Data HP, akun, placement, sesi, histori upload, dan aktivasi Remote Server tetap dipertahankan.

## Langkah Windows

1. Tutup Remote HP v1.48.
2. Buat salinan cadangan `remote_hp.db`.
3. Ekstrak `remote-hp-v1.50.zip` ke folder baru.
4. Salin `remote_hp.db` dari folder v1.48 ke root folder v1.50 **sebelum v1.50 pertama kali dijalankan**.
5. Jalankan `setup-windows.bat` bila `.venv` belum tersedia di folder baru.
6. Jalankan `jalankan-windows.bat`.

Pada startup pertama, migration menambahkan identitas HP stabil serta kolom transport USB/Wi-Fi. Tidak ada tabel HP/akun/histori yang dibangun ulang.

## Setelah upgrade

Buka **Pengaturan → Koneksi HP — USB & Wi-Fi Debugging**.

- HP yang sebelumnya memakai serial USB akan otomatis memiliki `usb_serial` yang sama.
- HP yang sebelumnya sudah memakai `ip:port` akan otomatis memiliki `wifi_endpoint` yang sama.
- Setiap HP memperoleh `stable_uid` satu kali dan ID tersebut tidak berubah saat berpindah USB ↔ Wi-Fi.
- Mode Auto memprioritaskan Wi-Fi bila online dan memakai USB sebagai fallback.

Token aktivasi Remote Server tetap berada di profil OS, sehingga tidak perlu kode aktivasi baru.
