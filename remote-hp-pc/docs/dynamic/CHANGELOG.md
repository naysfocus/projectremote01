# Changelog Dinamis

## v1.50 — Wireless ADB identity-safe

- Identitas HP dipisahkan dari transport USB/Wi-Fi.
- Wi-Fi endpoint disimpan per HP dan dapat reconnect otomatis.
- USB tetap menjadi fallback tanpa mengubah akun atau histori.
- Workflow push/scrcpy memakai target ADB yang sedang online.


## v1.48 — Sinkronisasi operasional Remote Server

- Inventaris HP, username akun, dan placement disinkronkan ke Remote Server v1.6.1.
- Progres upload disinkronkan per akun dan tanggal batch.
- Perubahan normal hanya mengirim sesi yang berubah; rekonsiliasi penuh berjalan saat startup dan berkala.
- Kredensial, caption, nama/path/file video tetap lokal.

## v1.46 — Akun bisa ditempatkan di banyak HP sekaligus

- **Perubahan struktural**: sebelumnya (v1.45) akun yang dipindah ke HP lain akan "menghilang" dari HP asalnya (exclusive, 1 akun = 1 HP). Sekarang, sesuai kebutuhan nyata di lapangan, **satu akun bisa ada di banyak HP sekaligus** — persis seperti kondisi kerja: HP-1 punya anisa.567, ayu.567, dea.567; HP-2 punya bella.567, anisa.567 (akun yang sama dengan HP-1), clara.567.
- Skema database diubah total: `accounts` kini murni identitas (kunci: username, unik case-insensitive), dipisahkan dari HP. Tabel baru `account_placements` menyimpan relasi *many-to-many* akun ↔ HP — satu akun boleh punya banyak placement (banyak HP), satu HP boleh menampung banyak placement (banyak akun).
- **Slot aplikasi (original/kloning) kini per-placement**, boleh berbeda di tiap HP. Contoh: anisa.567 bisa pakai slot "original" di HP-1 tapi "kloning" di HP-2 — keduanya sah, tidak saling mempengaruhi.
- Menambah akun dengan username yang **sudah ada** (di HP manapun) otomatis menambahkan **placement baru** ke akun tersebut — bukan membuat akun duplikat, dan tidak perlu konfirmasi tambahan (ini memang perilaku yang diinginkan).
- Riwayat, sesi, dan video upload tetap menempel ke satu `account_id` yang stabil, tidak peduli sudah diproses dari HP mana saja — sudah diuji: sesi dari HP-1 (dibatalkan karena baterai habis) dan sesi lanjutan dari HP-2 untuk akun yang sama, keduanya tampil utuh di satu riwayat gabungan.
- Menghapus akun kini menawarkan 2 pilihan jelas: **"Lepas dari HP Ini Saja"** (akun & seluruh riwayatnya tetap ada di HP lain, atau tersimpan sebagai akun "tanpa HP" bila ini placement terakhir) atau **"Hapus Akun Sepenuhnya"** (akun & seluruh riwayat di semua HP terhapus permanen).
- Sidebar menampilkan badge kecil (⇄) pada akun yang ditempatkan di lebih dari satu HP.
- Endpoint baru: `POST /api/accounts/<id>/placements`, `PUT /api/accounts/<id>/placements/<device_id>`, `DELETE /api/accounts/<id>/placements/<device_id>`.
- **Catatan**: karena ini perubahan skema database yang mendasar dan dirilis saat database masih tahap pengujian, tidak ada skrip migrasi dari struktur akun versi sebelumnya — instalasi baru langsung memakai skema v1.46.

## v1.45 — Auto-skip subfolder tidak layak & Akun lintas-HP

### 1) Auto-skip subfolder otomatis saat scan
- **Bug diperbaiki**: sebelumnya, kalau subfolder pertama (mis. `1/`) isinya tidak pas 24 video (kurang atau lebih), sistem berhenti di situ dan menampilkan error validasi — padahal subfolder berikutnya (mis. `2/`) bisa jadi sudah lengkap 24 video dan siap dipakai.
- Sekarang `/api/upload/scan` mencoba subfolder secara berurutan (nomor terkecil dulu) dan **otomatis lanjut ke subfolder berikutnya** bila subfolder yang dicoba: sedang dikunci sesi aktif akun lain, sudah selesai diproses, kosong, atau jumlah video siap upload (setelah dikurangi duplikat) tidak pas 24.
- Subfolder yang dilewati ditampilkan transparan di UI (badge ⏭ + catatan ringkas alasan dilewati), supaya jelas ini bukan bug — bukan cuma diam-diam meloncat.
- Response `/api/upload/scan` menyertakan field baru `skipped_subfolders` berisi daftar subfolder yang dilewati beserta alasannya.

### 2) Akun bisa dipakai di beberapa HP (identitas berbasis username, bukan HP)
- **Bug diperbaiki**: akun dengan username sama yang didaftarkan di HP berbeda sebelumnya dianggap 2 akun terpisah, sehingga riwayat/histori upload jadi terpecah dan membingungkan saat berpindah HP (mis. HP kehabisan baterai di tengah sesi, lanjut pakai HP lain).
- Kolom `accounts.device_id` sekarang bermakna **"HP tempat akun ini sedang/terakhir dipakai"**, bukan pemilik permanen. Riwayat, sesi, dan video tetap menempel ke `account_id` yang sama walau akun berpindah HP kapan pun.
- Saat menambah akun dengan username yang **sudah terdaftar** (di HP manapun), sistem tidak langsung membuat baris baru — menampilkan konfirmasi **"Pindahkan ke HP ini?"**. Jika dikonfirmasi, akun (beserta seluruh riwayat & sesinya) dipindahkan ke HP & slot aplikasi baru tanpa kehilangan data apa pun.
- Mengedit/rename akun ke username yang sudah dipakai akun lain juga dicegah (mencegah dua identitas berbeda punya nama sama).
- Sidebar tetap menampilkan akun terkelompok per HP seperti sebelumnya — akun otomatis "pindah" ke bawah HP yang sedang dipakainya.

## v1.44 — Perbaikan: folder/subfolder rebutan antar akun

- **Bug diperbaiki**: sebelumnya, saat sesi upload akun A masih `active` (termasuk saat sedang diistirahatkan di tengah jalan, belum diselesaikan/dibatalkan), subfolder yang sedang ia pakai bisa ikut ditawarkan ke akun B jika kebetulan memilih folder sumber video yang sama. Ini menyebabkan dua akun berpotensi memproses subfolder yang sama secara bersamaan.
- Menambahkan **kunci subfolder per sesi aktif**, tersimpan permanen di database (tabel `upload_sessions`, kolom `status = 'active'`) — bukan variabel sementara, sehingga tetap berlaku walau aplikasi ditutup & dibuka lagi selama sesi belum diselesaikan/dibatalkan.
- Endpoint `/api/upload/scan` kini otomatis melewati subfolder yang sedang dipakai sesi aktif akun lain, dan menandainya `locked: true` beserta `locked_by` (username akun yang memakainya).
- Endpoint `/api/upload/start` menambahkan **guard server-side terakhir**: walau melewati proses scan, permintaan mulai sesi pada subfolder yang sudah dikunci akun lain akan ditolak (`409 Conflict`) dengan pesan jelas menyebut akun mana yang sedang memakainya.
- UI Panel Upload menampilkan badge 🔒 pada subfolder yang sedang dipakai akun lain (di daftar subfolder saat scan) dan badge "Dipakai: <akun>" pada kartu sumber video (video-1 s.d. video-4) sebelum di-scan sama sekali.
- Akun yang sama tetap bisa melihat & melanjutkan subfolder miliknya sendiri (pengecualian berbasis `account_id`), sehingga alur "istirahat lalu lanjut lagi" tidak terganggu.
- Endpoint `/api/upload/sources` kini menyertakan ringkasan sesi aktif (`active_sessions`) per folder sumber video.

## v1.43 — Koneksi HP via WiFi (selain USB)

- Menambahkan toggle **Mode Koneksi HP** (USB / WiFi) di halaman Pengaturan.
- Toggle disimpan permanen di database (`connection_mode`, default **wifi**) — tidak kembali ke default saat aplikasi ditutup & dibuka lagi.
- Menambahkan 2 jalur setup WiFi:
  1. **Otomatis dari USB**: colokkan HP sekali via USB, klik "Aktifkan WiFi dari USB" → HP terdeteksi otomatis (`adb tcpip` + `adb connect`), lalu kabel boleh dicabut.
  2. **Manual tanpa USB** (Android 11+): pairing memakai kode 6 digit dari menu "Debugging Nirkabel" di HP (`adb pair` + `adb connect`).
- Endpoint baru: `GET/POST /api/devices/connection-mode`, `POST /api/devices/<id>/wifi/enable-from-usb`, `POST /api/devices/wifi/pair`, `POST /api/devices/<id>/wifi/connect`, `POST /api/devices/<id>/wifi/disconnect`.
- Serial HP otomatis berganti menjadi `ip:port` saat berhasil tersambung WiFi; seluruh fitur lain (push file, mirror scrcpy, dsb) berjalan tanpa perubahan karena hanya bergantung pada serial yang valid & online.
- **Catatan penting**: Android tetap mewajibkan setup awal sekali (USB *atau* buka menu Wireless Debugging) untuk pairing pertama kali — ini batasan protokol ADB/Android, bukan batasan aplikasi. Setelah pairing pertama berhasil, sesi berikutnya bisa 100% WiFi selama HP tidak reboot & IP tidak berubah.

## v1.42 — Paste caption Windows native dan cepat

- Menghapus ketergantungan PowerShell pada tombol Tempel ke HP di Windows.
- Memperbaiki error `[WinError 2] The system cannot find the file specified`.
- Mencari, memulihkan, dan memfokuskan jendela scrcpy langsung melalui WinAPI `user32.dll`.
- Mengirim `Ctrl+V` melalui WinAPI `SendInput` tanpa membuat proses eksternal.
- Mempertahankan jeda paste 0 ms dan lock FIFO agar workflow tetap cepat serta tidak menempel ganda.
- Menggunakan fallback `AttachThreadInput` saat Windows membatasi perpindahan foreground window.

## v1.41 — Fondasi server 24 post

- Menghapus pemilih policy `4`, `5`, `24`, `All`, dan `Manual` dari Panel Upload.
- Menetapkan satu kebijakan server: 24 video per sesi baru.
- Menolak batch subfolder yang tidak berisi tepat 24 video siap.
- Mempertahankan struktur folder flat lama dengan pemrosesan 24 video per sesi.
- Mengabaikan nilai policy dari client lama untuk mencegah bypass aturan.
- Menyimpan nilai policy 24 pada sesi baru agar database lama tetap kompatibel.
- Menyederhanakan Jadwal Default menjadi Aturan Jadwal 24 Post.
- Menetapkan jadwal sesi baru pada slot jam 00–23 dengan MM acak 01–15.
- Mempublikasikan capability read-only `posts_per_session: 24` dan `schedule_mode: fixed_24`.
- Menambahkan struktur dokumentasi statis dan dinamis.
