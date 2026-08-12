# Changelog

## v1.51.0

- **Perbaikan bug**: kegagalan dekripsi token lokal (mis. Windows DPAPI gagal
  membuka token setelah restart / ganti sesi login) sebelumnya membuang
  SELURUH konfigurasi lokal, termasuk `fingerprint_hash`. Akibatnya device
  terlihat seperti "device baru" bagi Remote Server dan aktivasi ulang
  selalu ditolak `already_activated` walau kode aktivasi baru sudah benar.
  Sekarang hanya token yang dibuang; identitas device (`fingerprint_hash`,
  `device_id`, dsb) tetap dipertahankan, sehingga aktivasi ulang dengan kode
  baru dari admin akan berhasil secara normal.
- Menaikkan `APP_VERSION` menjadi `1.51.0` (dikirim ke Remote Server saat
  aktivasi dan laporan aktivitas).
- Menambahkan test regresi (`test_token_decrypt_failure_only_clears_token_not_fingerprint`,
  `test_corrupt_config_file_still_resets_cleanly`) untuk mengunci perilaku ini.
- **Known issue (tidak diubah pada rilis ini)**: `test_manager_does_not_scan_and_only_reconnects_saved_endpoint`
  di `test_wireless_adb_v149.py` kadang gagal saat seluruh test suite
  dijalankan bersamaan (flaky, kemungkinan shared/global state antar test),
  walau selalu lulus saat dijalankan sendiri. Berkas ini tidak disentuh pada
  v1.51.0 dan berada di luar cakupan perbaikan aktivasi/token.

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
