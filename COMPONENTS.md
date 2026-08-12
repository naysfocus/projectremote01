# Matriks Kompatibilitas — Project Remote v1.0

| Komponen | Versi | Status | Kompatibilitas milestone |
|---|---:|---|---|
| Remote Server | 1.7 | Final Candidate | Remote HP PC 1.50.0, Video Mixer 1.22.1 |
| Remote HP PC | 1.50.0 | Final Candidate | Remote Server >=1.7, Android 1.0.0 |
| Video Mixer | 1.22.1 | Frozen | Remote Server >=1.6.1; v1.7 didukung |
| Remote HP Android | 1.0.0 | Final Candidate | Remote HP PC >=1.50.0 |

## Batas tanggung jawab

### Remote Server
- lisensi/aktivasi/revoke;
- lokasi, tag dan device;
- inventaris HP/akun Remote HP;
- transport ADB dan status Android Controller;
- agregasi progres dan laporan.

### Remote HP PC
- database operasional utama Remote HP;
- ADB USB/Wi-Fi dan fallback;
- push/delete/scrcpy;
- akun, placement, batch dan histori upload;
- Mobile API serta secure pairing Android;
- sinkronisasi metadata operasional ke Remote Server.

### Video Mixer
- proses video tetap lokal;
- laporan jumlah output ke Remote Server;
- tidak mengirim isi file video ke VPS.

### Remote HP Android
- controller LAN untuk Remote HP PC;
- setup/resume sesi;
- overlay dan clipboard caption;
- tidak menjadi automation bot TikTok.
