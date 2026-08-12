# Remote HP Android v1.0.0

Companion app untuk **Remote HP PC v1.50+**. Android berbicara hanya ke Remote HP PC melalui LAN tepercaya; Android tidak berkomunikasi langsung dengan Remote Server/VPS.

## Fungsi utama

- pairing sekali pakai melalui QR/deep link atau kode manual;
- bearer token disimpan terenkripsi dengan Android Keystore;
- setup akun, tanggal batch, sumber video, dan batch 24 video;
- resume sesi aktif setelah aplikasi/restart;
- floating overlay Bubble, Compact, dan Expanded;
- workflow satu tombol mengikuti state server: KIRIM → caption → SELESAI;
- caption disalin ke clipboard Android;
- foreground service selama overlay aktif;
- tanpa Accessibility Service dan tanpa auto-click TikTok.

## Kompatibilitas

- Remote HP PC >= 1.50
- Remote Server >= 1.7 untuk monitoring ekosistem (Android tetap tidak mengakses VPS)
- Android 8.0 / API 26 atau lebih baru

## Build

Buka folder ini langsung melalui Android Studio. Petunjuk langkah demi langkah ada di `BUILD-APK.md`.

## Jaringan

PC dan HP harus berada pada LAN/Wi-Fi yang sama. Jalankan Remote HP PC dengan `jalankan-windows-lan.bat` atau `jalankan-ubuntu-lan.sh` saat Android Controller digunakan. Mobile API menolak koneksi non-LAN.
