# Release Notes — Project Remote v1.0

Project Remote v1.0 menyatukan dua jalur pengembangan lama (VPS monitoring dan Android companion) menjadi satu baseline resmi.

## Remote Server 1.7
- monitoring transport ADB USB/Wi-Fi per HP;
- monitoring Android Controller paired/online;
- migration 0007 non-destructive;
- dashboard Remote HP/site diperluas;
- kompatibel dengan Remote HP PC 1.50.0.

## Remote HP PC 1.50.0
- mempertahankan Wireless ADB foundation 1.49;
- Mobile API LAN untuk Android Controller;
- pairing code sekali pakai dan bearer token hashed;
- QR pairing;
- server/local session state sebagai sumber kebenaran;
- push/caption-ready/confirm/finish/cancel;
- cache sumber video Android hanya direfresh dari admin PC;
- sinkronisasi status Android Controller dan transport ADB ke VPS;
- launcher LAN terpisah agar exposure jaringan tidak menjadi default.

## Video Mixer 1.22.1
Tidak berubah pada milestone ini dan dibekukan sebagai baseline kompatibel.

## Remote HP Android 1.0.0
- project Android Studio terpisah dengan versioning sendiri;
- secure token storage menggunakan Android Keystore;
- QR deep-link pairing;
- setup dan resume sesi;
- Bubble, Compact, Expanded overlay;
- satu tombol utama mengikuti state server lokal;
- clipboard caption;
- foreground service;
- tanpa Accessibility Service dan tanpa auto-click TikTok.

## Packaging baru
Semua release selanjutnya dikirim sebagai satu `project-remote-v1.X.zip` lengkap. Nomor versi komponen tetap dipertahankan secara independen di dalamnya.
