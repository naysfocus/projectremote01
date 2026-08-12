# Changelog

## v1.50.0

- Memisahkan identitas HP (`stable_uid`) dari transport ADB USB/Wi-Fi.
- Menambahkan `usb_serial`, `wifi_endpoint`, preferensi transport per HP, dan auto reconnect.
- Wi-Fi menjadi jalur utama pada mode Auto; USB otomatis menjadi fallback bila Wi-Fi tidak tersedia.
- Menghentikan perilaku lama yang mengganti kolom serial HP menjadi `ip:port` saat Wi-Fi aktif.
- Push video, hapus file, scrcpy, dan paste caption kini selalu memakai transport ADB yang benar-benar online.
- Menambahkan status transport langsung pada sidebar dan panel pengaturan Wireless Debugging yang lebih jelas.
- Menambahkan reconnect/disconnect manual serta penyimpanan endpoint tanpa mengubah ID HP.
- Sinkronisasi Remote Server tetap memakai `client_device_id`, sehingga perpindahan transport tidak membuat handset baru di server.
- Menambahkan migration idempotent dari v1.48 tanpa menghapus HP, akun, placement, sesi, atau histori upload.

## v1.48.0

- Menambahkan sinkronisasi inventaris HP, akun, dan placement ke Remote Server v1.6.1.
- Menambahkan progres upload per akun dan tanggal batch.
- Menambahkan sinkronisasi incremental untuk sesi yang berubah serta full reconciliation berkala.
- Menambahkan antrean ulang otomatis ketika internet/server sementara tidak tersedia.
- Menjaga data kredensial dan file media tetap lokal.
- Mempertahankan aktivasi, heartbeat, revoke, grace period, ADB, scrcpy, serta database v1.47.
