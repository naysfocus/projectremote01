# Urutan Deployment Project Remote v1.0

## 1. VPS — Remote Server 1.7
Baca `remote-server/UPGRADE_FROM_V1.6.1.md`. Pastikan backup tersedia. Jangan hapus volume Docker.

## 2. PC — Remote HP 1.50.0
Baca `remote-hp-pc/UPGRADE_FROM_V1.49.md`. Backup dan salin `remote_hp.db` sesuai panduan sebelum menjalankan versi baru.

Mode normal hanya bind localhost. Saat melakukan pairing/operasi Android pada LAN tepercaya, gunakan launcher `jalankan-windows-lan.bat` atau `jalankan-ubuntu-lan.sh`.

## 3. Video Mixer 1.22.1
Tidak berubah pada Project Remote v1.0. Jalankan sesuai README komponen.

## 4. Android — Remote HP Android 1.0.0
Baca `remote-hp-android/BUILD-APK.md`. Development/build dilakukan menggunakan Android Studio. APK production sebaiknya ditandatangani dengan keystore yang disimpan sendiri dan tidak dimasukkan ke source ZIP.
