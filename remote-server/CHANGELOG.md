# Changelog

## v1.8

- **Perbaikan bug**: aktivasi ulang dari device dengan fingerprint yang sama
  (mis. token lokal client hilang setelah restart) sebelumnya SELALU
  ditolak dengan `already_activated (409)`, walaupun admin sudah membuat
  kode aktivasi baru yang valid untuk device tersebut. Sekarang, jika
  fingerprint device cocok dengan device yang sudah pernah teraktivasi
  untuk `app_type` yang sama, mengirim kode aktivasi baru yang valid akan
  menerbitkan ulang token pada baris `AppAuthorization` yang sama (token
  lama otomatis menjadi tidak valid), alih-alih menolak permintaan. Ini
  juga sekaligus memperbaiki tombol **Revoke → Aktifkan kembali** di
  dashboard admin, yang sebelumnya tidak benar-benar membuka jalan aktivasi
  ulang karena pengecekan lama tidak memfilter berdasarkan status.
- Perilaku ini tetap aman: `UniqueConstraint(device_id, app_type)` dijaga
  (tidak ada baris `AppAuthorization` duplikat), dan device dengan
  fingerprint yang benar-benar berbeda tidak terpengaruh sama sekali.
- Menambahkan test regresi `test_reactivation_with_new_code_reissues_token_for_same_device`.

## v1.7

- Menambahkan mirror inventaris HP, akun, dan penempatan akun dari Remote HP v1.48.
- Menambahkan progres upload per akun dan tanggal batch.
- Menambahkan ringkasan 31 tanggal batch, filter akun/HP, serta riwayat sesi terbaru.
- Menambahkan full reconciliation untuk histori yang dihapus secara lokal tanpa hard-delete server.
- Menyinkronkan sesi Remote HP ke `work_jobs` agar progres aktif tampil pada lokasi dan device.
- Menambahkan endpoint inventory, session sync, dan session reconciliation khusus token Remote HP.
- Menjaga informasi sensitif tetap di komputer client.
- Migration `0006` mempertahankan device, otorisasi, laporan, lokasi, tag, integrasi, dan akun admin v1.6.

## v1.6.0

- Menambahkan Lokasi/Site dengan zona WIB, WITA, atau WIT.
- Menambahkan tag device dan filter lokasi.
- Mengganti nama tampilan `matrix_generator` menjadi Video Mixer tanpa mengubah ID internal.
- Menambahkan statistik operasional per lokasi dan fondasi `work_jobs`.

## v1.5.1

- Finalisasi branding Remote Server, readiness test, secure cookie otomatis, serta kompatibilitas volume lama.
