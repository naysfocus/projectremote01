# Certification Checklist — Project Remote v1.0

Checklist ini sengaja ditunda sampai tersedia perangkat fisik. Release tidak boleh disebut **Physical Certified / Production Certified** sebelum bagian yang relevan lulus.

## A. Remote Server
- [ ] Upgrade dari data produksi tanpa kehilangan akun admin, device, lokasi, token integrasi, laporan dan backup.
- [ ] Tiga container healthy setelah restart VPS.
- [ ] Domain HTTPS, Telegram, dashboard lokasi dan detail Remote HP bekerja.

## B. Remote HP PC
- [ ] Database lama terbaca tanpa kehilangan HP, akun, placement dan histori.
- [ ] Aktivasi persisten, heartbeat, revoke dan grace period bekerja.
- [ ] ADB USB bekerja.
- [ ] Wireless ADB pairing/connect/reconnect bekerja.
- [ ] Wi-Fi→USB dan USB→Wi-Fi fallback tidak membuat HP duplikat.
- [ ] scrcpy, push, delete, caption dan confirm tidak regresi.

## C. Android Controller
- [ ] Project berhasil Gradle Sync dan build di Android Studio.
- [ ] APK dapat dipasang pada HP fisik.
- [ ] QR pairing sekali pakai berhasil.
- [ ] Token tidak muncul pada UI/log/clipboard.
- [ ] Overlay permission dan foreground service bekerja.
- [ ] Bubble, Compact dan Expanded bekerja.
- [ ] Restart Android memulihkan sesi aktif.
- [ ] Revoke dari PC memutus akses Android.

## D. Workflow 24/24
- [ ] Setup akun + tanggal + sumber video.
- [ ] KIRIM menggunakan transport ADB aktif.
- [ ] Caption tersalin dan state menjadi SELESAI.
- [ ] Confirm maju tepat satu item.
- [ ] 24/24 selesai tanpa item ganda/terlewati.
- [ ] Remote Server menunjukkan akun, tanggal batch dan jumlah video yang benar.

## E. Multi-device dan recovery
- [ ] Dua HP bersamaan.
- [ ] Empat atau lebih HP sesuai kondisi lapangan.
- [ ] Wi-Fi putus/tersambung kembali.
- [ ] PC restart.
- [ ] VPS restart.
- [ ] Android restart.
- [ ] Rekonsiliasi laporan setelah offline tidak menggandakan hitungan.
