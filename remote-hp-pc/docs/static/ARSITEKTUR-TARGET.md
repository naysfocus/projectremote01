# Arsitektur Target Remote HP

## Tiga area pengembangan

Remote HP dikembangkan dalam tiga area yang terpisah tetapi memakai satu model data dan satu workflow:

1. **Server PC** — otak sistem, database, penyimpanan video, caption, jadwal, histori, pairing perangkat, dan API.
2. **Client Android** — aplikasi yang dipasang pada HP yang memang dipakai untuk upload TikTok.
3. **Dokumentasi** — keputusan statis dan status implementasi dinamis.

## Topologi target

Satu PC berjalan sebagai server lokal. Semua HP berada pada jaringan Wi-Fi yang sama dengan PC. Jika tersedia 10 HP operasional, aplikasi Android dipasang pada seluruh 10 HP tersebut.

Setiap instalasi Android hanya mengoperasikan HP tempat aplikasi itu dipasang. Satu HP tidak menjadi remote untuk HP lain.

```text
PC Server
├── Web Super Admin
├── SQLite/database server
├── File dan folder video
├── Generator caption
├── Generator jadwal
├── Histori dan guard duplikasi
├── Pairing perangkat
└── API lokal

Wi-Fi lokal

HP 1 ─ Aplikasi Android terikat ke HP 1 ─ TikTok
HP 2 ─ Aplikasi Android terikat ke HP 2 ─ TikTok
...
HP N ─ Aplikasi Android terikat ke HP N ─ TikTok
```

## Alur client Android target

Setelah pairing satu kali, operator tidak perlu login dan tidak perlu memilih HP.

```text
Buka aplikasi
→ perangkat dikenali otomatis
→ pilih akun TikTok
→ pilih tanggal
→ pilih folder video
→ mulai Mode Cepat
```

Mode Cepat:

```text
Kirim Video N ke HP
→ Isi Caption
→ Selesai – HH:MM
→ lanjut ke video berikutnya
```

## Pairing dan autentikasi

ADB serial wajib menjadi identitas operasional di sisi server, tetapi bukan rahasia autentikasi. Pairing satu kali menghasilkan `app_device_uuid` dan token perangkat. Seluruh request Android memakai token tersebut; server menentukan perangkat dari token dan tidak mempercayai `device_id` bebas dari client.

Tidak ada login username/password operator pada target awal. Super Admin dapat mencabut pairing, menonaktifkan perangkat, atau melakukan pairing ulang.

## Folder video target

Empat folder baku saat ini akan diganti secara bertahap dengan koleksi video dinamis yang dibuat Super Admin, misalnya `Peronika Dress`. Setiap koleksi dapat memiliki 1 sampai N batch. Setiap batch berisi tepat 24 video.

Nama tampilan dan folder fisik dipisahkan:

```text
Nama tampilan : Peronika Dress
Folder key    : peronika-dress
Batch         : 001, 002, ... N
Isi batch     : tepat 24 video
```

## Prinsip kompatibilitas

Migrasi dilakukan bertahap. Web PC dan workflow ADB/scrcpy yang sudah stabil tetap dapat dipakai sampai client Android siap. API dan database lama hanya dihapus setelah data serta workflow penggantinya teruji.
