# Wireless ADB — Remote HP v1.50

## Konsep

Remote HP menganggap **HP fisik** sebagai identitas tetap. USB dan Wi-Fi hanyalah dua jalur ADB menuju HP yang sama.

- `stable_uid`: identitas lokal HP, tidak berubah.
- `usb_serial`: serial ketika HP tersambung USB.
- `wifi_endpoint`: alamat `IP:Port` Wireless Debugging.
- `preferred_transport`: Auto, Wi-Fi, atau USB.
- `wifi_auto_reconnect`: mencoba kembali endpoint Wi-Fi yang sudah disimpan dengan interval rendah.

Pada **Auto**, Remote HP memilih Wi-Fi bila online. Jika Wi-Fi putus tetapi USB masih online, workflow otomatis memakai USB.

## Cara 1 — dari USB sekali

1. Pastikan PC dan HP berada di jaringan Wi-Fi yang sama.
2. Aktifkan USB Debugging.
3. Sambungkan HP ke PC dengan kabel.
4. Di Remote HP buka **Pengaturan → Koneksi HP**.
5. Pilih HP pada bagian **Aktifkan Wi-Fi dari USB sekali**.
6. Klik **Aktifkan Wi-Fi dari USB**.
7. Setelah status Wi-Fi online, kabel dapat dicabut.

Remote HP menyimpan serial USB dan endpoint Wi-Fi secara terpisah.

## Cara 2 — Wireless Debugging Android 11+

1. Di HP buka **Opsi Pengembang → Debugging Nirkabel**.
2. Pilih **Pasangkan perangkat dengan kode pairing**.
3. Masukkan `IP:Port Pairing` dan kode 6 digit ke Remote HP, lalu klik **Pasangkan**.
4. Kembali ke halaman Wireless Debugging HP dan lihat `IP address & Port` untuk koneksi ADB.
5. Pilih HP yang sudah terdaftar di Remote HP.
6. Masukkan `IP:Port Koneksi`, lalu klik **Hubungkan & Simpan**.

Port pairing dan port koneksi dapat berbeda. Jangan menukar keduanya.

## Reconnect

Auto reconnect hanya mencoba endpoint yang sudah pernah disimpan. Remote HP **tidak melakukan scan LAN** dan tidak menebak bahwa sebuah endpoint baru adalah HP tertentu.

Jika Wireless Debugging dimatikan/restart dan Android memberikan port koneksi baru, masukkan endpoint baru sekali pada HP yang sama. Akun dan histori tidak berubah karena identitas HP tidak menggunakan IP/port.

## Status sidebar

- `📶 Wi-Fi`: workflow sedang menggunakan ADB Wi-Fi.
- `🔌 USB`: workflow sedang menggunakan USB; Wi-Fi boleh tetap tersimpan sebagai fallback.
- `○ Offline`: tidak ada transport tersimpan yang sedang online.
