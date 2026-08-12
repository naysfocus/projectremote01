# Remote HP PC v1.50

Remote HP PC adalah engine lokal untuk ADB/scrcpy, akun, sesi upload dan database operasional. v1.50 menggabungkan baseline v1.49 Wireless ADB dengan Mobile API/Android Controller dari cabang pengembangan lama.

## Fitur utama v1.50

- seluruh fitur v1.49 Wireless ADB: identitas HP stabil, USB/Wi-Fi transport, reconnect, USB fallback;
- sinkronisasi HP, akun, placement dan progres upload ke Remote Server v1.7;
- Mobile API hanya untuk LAN tepercaya;
- pairing Android one-time + QR/deep link;
- bearer token Android hanya disimpan sebagai hash di PC;
- pairing management hanya dapat dilakukan dari loopback/PC;
- cache setup video yang hanya direfresh dari tindakan admin PC; Android tidak menjalankan scan folder otomatis;
- session bootstrap/resume;
- state-driven `push`, `caption-ready`, `confirm`, `finish`, `cancel`;
- data sensitif akun, caption, path dan file video tidak dikirim ke VPS.

## Menjalankan

Mode normal:
`jalankan-windows.bat`

Mode Android Controller/LAN:
`jalankan-windows-lan.bat`

Alamat PC tetap port 5001. Saat mode LAN aktif, izinkan Python/Remote HP hanya pada **Private Network** Windows Firewall.

## Kompatibilitas

- Remote Server >= 1.7
- Remote HP Android >= 1.0.0
- Remote Server activation internal app type tetap `remote_hp`.
