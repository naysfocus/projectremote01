# PROGRES

## v1.42 — Perbaikan Tempel Caption Windows Native ✅

- Akar error `[WinError 2]` ditemukan pada pemanggilan executable `powershell` setiap tombol Tempel ke HP ditekan.
- Fokus jendela scrcpy dipindahkan ke WinAPI native memakai `ctypes`, tanpa dependency baru.
- `Ctrl+V` dikirim langsung melalui `SendInput`, sehingga tidak perlu spawn proses PowerShell.
- Fallback `AttachThreadInput` ditambahkan agar fokus tetap andal saat foreground-lock Windows aktif.
- Jeda paste tetap 0 ms, sedangkan lock paste dan guard FIFO tetap dipertahankan.
- Cache aset dan judul aplikasi dinaikkan ke v1.42.

## v1.41 — Fondasi server 24 post dan dokumentasi bertingkat

- Policy `4`, `5`, `All`, dan `Manual` dihapus dari UI.
- Semua sesi baru dipaksa server menjadi tepat 24 video; nilai policy client lama diabaikan.
- Subfolder batch wajib tepat 24 video siap, sementara folder flat legacy diproses 24 video per sesi.
- Jadwal sesi baru memakai 24 slot jam `00–23` dengan MM acak `01–15`.
- Panel Jadwal Default disederhanakan menjadi Aturan Jadwal 24 Post.
- Ditambahkan `docs/static/` untuk keputusan stabil dan `docs/dynamic/` untuk status versi.

## v1.40 — Perbaikan MM Jadwal Post 01–15 ✅

- Akar masalah ditemukan pada `_even_spread()`: jumlah post seperti 10/14 disebar berdasarkan total menit sehingga base dapat menjadi `02:24`, `01:43`, dan sejenisnya.
- Jadwal Default dengan menit nonnol kemudian menambah sumber komponen MM kedua, sehingga hasil terlihat keluar dari rentang yang dimaksud.
- Jadwal Default sekarang dinormalisasi menjadi slot `HH:00`; komponen MM hanya dibuat oleh randomizer.
- MM hasil jadwal selalu berada pada `01..15`; nilai setting lama 0, 20, 30, atau rusak dipulihkan otomatis ke batas aman.
- Penyebaran 10/14/24 post tetap merata sepanjang 24 jam, tetapi seluruh base menggunakan `HH:00`.
- Route sesi baru dan Generate Ulang Jadwal memakai normalisasi yang sama.
- Cache aset dan judul aplikasi dinaikkan ke v1.40.

## v1.39 — Delay Tombol Selesai 2 Detik ✅

- Setelah Tempel ke HP/Isi Caption berhasil, tombol Selesai ditahan selama 2 detik.
- Panel 2 dan Panel 4 memakai timestamp, timer, dan guard konfirmasi yang sama.
- Tombol Mode Cepat tetap muncul sebagai langkah ketiga tetapi nonaktif selama masa tunggu.
- Guard fungsi konfirmasi mencegah pemanggilan selesai lebih awal dari console/script.
- Cache aset dan judul aplikasi dinaikkan ke v1.39.

## v1.37 — Fallback Caption & Panel Ringkas ✅

- Tempel ke HP/Isi Caption otomatis generate ulang jika caption kosong, maksimal 3 percobaan.
- Kolom log Panel 2 serta isi Caption & Hashtag Panel 3 dapat hide/unhide; default tetap tampil.
- Header Mode Cepat menampilkan Post N/Total di kiri dan HH:MM post berlangsung di kanan.
- Cache aset dan judul aplikasi dinaikkan ke v1.37.

## v1.36 — Mode Cepat Tiga Langkah ✅

- Panel baru **Mode Cepat** ditempatkan sebagai Panel 4.
- Panel Jadwal Post (TikTok Studio) digeser menjadi Panel 5.
- Workflow ringkas: **Kirim Video N ke HP → Isi Caption → Selesai - HH:MM**.
- Tombol muncul bertahap dari kanan; tombol tahap sebelumnya bergeser ke kiri dan menjadi disabled setelah sukses.
- Tombol kirim memakai push FIFO yang sudah ada dan tetap memicu generate ulang caption otomatis.
- Tombol Isi Caption memakai auto-paste scrcpy tanpa delay dari v1.35.
- Semua tombol Mode Cepat berbagi fungsi inti dengan panel lama agar guard, histori, status, dan fallback tetap konsisten.
- Cache aset dan judul aplikasi dinaikkan ke v1.36.

## v1.35 — Tempel Tanpa Delay ✅

- Jeda fokus sebelum `Ctrl+V` dihapus dari 50 ms menjadi **0 ms**.
- Setelah jendela scrcpy berhasil diaktifkan, shortcut paste langsung dikirim.
- Tidak ada `sleep` yang disengaja sebelum paste pada Windows maupun Linux.
- Auto-split tanpa rongga dari v1.34 tetap dipertahankan.
- Cache aset dan judul aplikasi dinaikkan ke v1.35.

---

## v1.34 — Tempel 50 ms & Split Windows Tanpa Rongga ✅

- Jeda fokus sebelum `Ctrl+V` diturunkan dari 200 ms menjadi **50 ms**.
- Auto-split Windows membaca visible frame melalui `DWMWA_EXTENDED_FRAME_BOUNDS`.
- Resize border transparan/bayangan DWM dikompensasi saat browser dan scrcpy diposisikan.
- Frame visual browser menempel ke kiri, scrcpy menempel ke kanan, dan keduanya bertemu tepat di garis split.
- Tinggi frame visual tetap mengikuti work area monitor sehingga bagian bawah menempel tepat di atas taskbar.
- Fallback lama tetap dipakai bila API DWM tidak tersedia.
- Cache aset dan judul aplikasi dinaikkan ke v1.34.

## v1.33 — Tempel 200 ms & Auto Split Mirror ✅

- Jeda fokus sebelum `Ctrl+V` diturunkan dari 350 ms menjadi **200 ms**.
- Saat Mirror dibuka, scrcpy otomatis didok ke kanan dengan tinggi mengikuti work area monitor.
- Browser Remote HP otomatis diposisikan di kiri agar membentuk split workspace.
- Klik icon Mirror saat jendela sudah terbuka akan merapikan ulang posisi browser dan scrcpy.
- Lebar scrcpy dihitung dari rasio layar HP (`adb shell wm size`) dengan fallback rasio 9:20.
- Windows memakai WinAPI bawaan; Ubuntu memakai `xdotool` secara best-effort.
- Cache aset dan judul aplikasi dinaikkan ke v1.33.

## v1.32 — Tempel Caption Otomatis ke HP ✅

- Panel 3 memakai urutan tombol: **Generate Ulang → Copy Semua → Tempel ke HP**.
- Tombol **Tempel ke HP** menyalin caption ke clipboard PC, memfokuskan scrcpy HP sesi aktif, lalu mengirim `Ctrl+V`.
- Windows memakai PowerShell/WScript bawaan; Ubuntu memakai `xdotool`.
- Tombol memiliki state proses untuk mencegah klik ganda.
- **Copy Semua** tetap dipertahankan sebagai fallback manual.
- Tombol **Selesai - HH:MM** terbuka setelah salah satu jalur caption berhasil.
- Generate Ulang, pengiriman video baru, dan perpindahan video mereset status caption.
- Cache aset dan judul aplikasi dinaikkan ke v1.32.

## v1.31 — Empat Sumber Video Tetap & Root Project Lebih Bersih ✅

- Panel 2 Upload diubah dari input path menjadi empat kartu sumber: Video 1–4.
- Root sumber tetap dikonfigurasi dari menu Pengaturan.
- Backend otomatis membuat `video-1` sampai `video-4` dan menampilkan jumlah batch/video.
- Folder `video` lama dimigrasikan aman ke `video-1` saat database lama dibuka.
- Dokumentasi pendukung dipindahkan ke folder `docs/` agar root project lebih bersih.
- Cache aset dan judul aplikasi dinaikkan ke v1.31.

# 📱 PROGRES — Remote HP

> Dokumen hidup untuk melacak pengerjaan aplikasi **Remote HP**
> Setiap checkpoint = ZIP baru dengan versi `v1.0X`
> Port aplikasi: **5001** (port 5000 dipakai Video Mixer)

---

## 📌 Versi Saat Ini: **v1.40** ✅

| Versi | Status | Ringkasan |
|---|---|---|
| **v1.40** | ✅ SELESAI | Perbaikan generator Jadwal Post: MM konsisten 01–15 dan setting lama dinormalisasi |
| **v1.39** | ✅ SELESAI | Delay 2 detik sebelum tombol Selesai aktif setelah auto-paste caption |
| **v1.37** | ✅ SELESAI | Fallback generate caption 3x, hide/unhide log dan caption, indikator jam Mode Cepat |
| **v1.36** | ✅ SELESAI | Mode Cepat tiga langkah dengan tombol progresif: kirim video, isi caption, selesai |
| **v1.35** | ✅ SELESAI | Tempel caption tanpa jeda fokus (0 ms); Ctrl+V dikirim segera setelah scrcpy aktif |
| **v1.34** | ✅ SELESAI | Tempel caption 50 ms + kompensasi frame Windows agar split tanpa rongga |
| **v1.33** | ✅ SELESAI | Tempel caption 200 ms + auto split browser kiri dan scrcpy kanan |
| **v1.32** | ✅ SELESAI | Tempel caption otomatis ke kolom aktif melalui scrcpy, dengan Copy Semua sebagai fallback |
| **v1.00–v1.04** | ✅ SELESAI | Fondasi → Services → Upload FIFO → Jadwal → History |
| **v1.05** | ✅ SELESAI | Setup turnkey 1-klik (Windows + Ubuntu) |
| **v1.06** | ✅ SELESAI | Fix ".venv rusak tanpa pip" + rapikan perintah copy-paste |
| **v1.07** | ✅ SELESAI | Rombak total UI/UX (routing benar + desain profesional) |
| **v1.08** | ✅ SELESAI | Fix jadwal maju-saja + folder video bawaan + Settings fungsional |
| **v1.09** | ✅ SELESAI | Hapus Jadwal Generator redundan + kolom jam berubah warna |
| **v1.10** | ✅ SELESAI | Tombol Mirror layar HP (scrcpy) + auto-install scrcpy |
| **v1.11** | ✅ SELESAI | Anti jendela mirror dobel (1 jendela per HP, klik ulang = fokus) + debug off untuk stabilitas |
| **v1.1.2** | ✅ SELESAI | Mode mirror: anti-sleep (`--stay-awake`) + opsi matikan layar HP (`--turn-screen-off`) di Pengaturan |
| **v1.1.3** | ✅ SELESAI | Policy upload jadi 4/5/24/All/Manual + jadwal post mengikuti jumlah video (4→3 jam siang, 24→tiap jam) dengan rentang acak tetap |
| **v1.1.4** | ✅ SELESAI | **Panel Tanggal (Panel 1) dengan kalender + anti-duplikasi berbasis (nama file + tanggal batch): nama file sama boleh diupload ulang asalkan beda tanggal** |
| **v1.1.5** | ✅ SELESAI | **Anti-duplikasi tidak lagi memblokir berdasarkan riwayat + Audit kompatibilitas Windows + PATCH galeri media-scan + PATCH tuning scrcpy realtime** |
| **v1.1.6** | ✅ SELESAI | Checkpoint pemeliharaan (basis untuk v1.1.7) |
| **v1.1.7** | ✅ SELESAI | Akun dikelompokkan per SLOT APLIKASI dalam tiap HP (Aplikasi Original / Aplikasi Kloning — Aplikasi Ganda Xiaomi/Redmi, maks 8 akun/slot = 16/HP) + menu WORKFLOW OTOMATISASI berbasis Maestro (rekam via Maestro Studio → download → modifikasi → upload → simpan → eksekusi `maestro test` ke HP dengan log live). |
| **v1.1.8** | ✅ SELESAI | (1) Setup script auto-install Java 17+ & Maestro CLI (ikut pola ADB/scrcpy). (2) Eksekusi Maestro menerima variabel injeksi `-e KEY=VALUE` (ACCOUNT_NAME, CAPTION, dll) + DELAY_MS di-acak otomatis di sisi server per eksekusi (rentang diatur di Pengaturan). (3) Overhaul caption: hashtag dipaksa maks 3 di generate_caption(), template bawaan diganti total ke gaya netral psikologi konsumen (tanpa over-claim/checkout), + validator flag_risky_caption() yang memperingatkan (bukan memblokir) saat menyimpan template berisiko. |
| **v1.1.9** | ✅ SELESAI | PATCH `setup-windows.bat`: (a) unduhan Maestro CLI via PowerShell kini menekan progress-bar (`$ProgressPreference='SilentlyContinue'` + `-UseBasicParsing`) yang sebelumnya membuat output konsol berantakan/lambat; (b) pengunduhan Maestro (±200MB) kini DILEWATI dulu bila Java 17+ belum siap — selaras dengan `setup-ubuntu.sh` — supaya tidak buang waktu/bandwidth untuk sesuatu yang belum bisa dipakai. |
| **v1.1.10** | ✅ SELESAI | `setup-windows.bat`: langkah BARU [1/8] auto-install winget sendiri bila belum ada — coba daftar-ulang App Installer, kalau gagal unduh & pasang `Microsoft.DesktopAppInstaller` (+ VCLibs) dari link resmi Microsoft, tanpa buka Store manual. Ditempatkan SEBELUM Python; PATH sesi disegarkan agar langkah setelahnya langsung pakai. Ada fallback manual bila gagal. |
| **v1.1.11** | ✅ SELESAI | 3 perbaikan dari laporan user: (1) Caption bawaan LAMA (over-claim) di DB lama otomatis diganti jadi 10 caption netral via migrasi `_migrate_old_caption_seeds()` — caption buatan user TIDAK tersentuh. (2) "Buka Perekam" tidak lagi membuka localhost:9999 KOSONG di Maestro CLI 2.6+ (studio web sudah dihapus Maestro) — versi CLI dideteksi; kalau 2.6+ tanpa Studio Desktop, tampilkan panduan jelas + perintah `maestro record`, bukan halaman kosong. (3) Bug kosmetik `setup-windows.bat`: `&` telanjang di satu echo di-escape jadi `^&` (hilangkan error "'langsung' is not recognized"). |
| **v1.1.12** | ✅ SELESAI | PEROMBAKAN BESAR atas permintaan user: Maestro DIHAPUS TOTAL (kode, endpoint, UI, dependency Java) — diganti perekam Workflow berbasis ADB MURNI. Rekam: buka mirror scrcpy + tangkap `getevent` di background saat user beraktivitas; olah jadi langkah bersih (tap/swipe/text/keyevent) dengan deteksi elemen opsional via `uiautomator dump` (fallback ke koordinat kalau gagal). Tinjau & edit langkah (hapus/urutkan/ubah teks/jeda) sebelum simpan sbg skrip `.json` di folder `scripts/`. Eksekusi via `adb shell input ...` dengan jeda acak antar-langkah (setting baru `step_delay_min_ms`/`max_ms`, default 300-1200ms) + dukungan variabel teks (`text_var`, mis. CAPTION beda per akun) sebagai pengganti fitur -e KEY=VALUE Maestro. Setup script (`setup-windows.bat`/`setup-ubuntu.sh`) dirampingkan: langkah Java 17+ & Maestro CLI dihapus total (Windows 8→6 langkah, Ubuntu 7→5 langkah). Migrasi otomatis membersihkan setting era-Maestro dari DB lama. |
| **v1.1.13** | ✅ SELESAI | PATCH KRUSIAL: perekam ADB (v1.1.12) ternyata 0 langkah terekam di HP nyata (Redmi 14C) walau sudah beraktivitas — akar masalah: `adb shell getevent` dipanggil non-interaktif membuat Android menahan output di buffer internal (bukan streaming langsung), sehingga data hilang begitu proses dihentikan saat "Stop & Tinjau". Diperbaiki dengan memaksa alokasi pseudo-terminal (`adb shell -tt ...`) supaya Android mengirim tiap event secara langsung. Ditambah peringatan dini di UI kalau sudah >8 detik rekam tapi 0 langkah terdeteksi. |
| **v1.1.14** | ✅ SELESAI | Fitur WORKFLOW DIHAPUS TOTAL atas permintaan user, setelah ditemukan batasan fundamental: sentuhan lewat mirror scrcpy TIDAK BISA direkam ADB — scrcpy menyuntikkan event lewat Android InputManager (jalur software terpisah), bukan lewat device sentuh fisik yang didengarkan `getevent`, sehingga HP merespons visual tapi `getevent` tidak pernah melihat sentuhan itu. Dihapus: `services/recorder.py`, `routes/workflow.py`, `static/workflow.js`, folder `scripts/`, menu & halaman Workflow di UI, tabel `workflow_runs`, semua setting terkait — dengan migrasi otomatis yang membersihkan DB lama user. |
| **v1.1.15** | ✅ SELESAI | 2 perbaikan fitur Upload: (1) Video yang dihapus dari HP kini otomatis membersihkan entri MediaStore lewat `content delete` (+ broadcast scan sbg fallback) — sebelumnya Galeri masih menampilkan/nyangkut file lama sampai HP di-restart karena hanya `rm` filesystem tanpa memberi tahu MediaStore. (2) Video kini otomatis `touch` ke tanggal SEKARANG (di HP, bukan mengubah file asli di PC) tepat sebelum media scan saat push — supaya video selalu tampil di urutan PALING ATAS/TERBARU di Galeri. |
| **v1.1.16** | ✅ SELESAI | PATCH: Galeri masih belum refresh realtime setelah hapus (v1.1.15) — akar masalah: broadcast `MEDIA_SCANNER_SCAN_FILE` ke path FOLDER/file yang sudah hilang tidak reliable di Android modern (DEPRECATED sejak API 29). Diperbaiki dengan `rescan_volume()` — `adb shell content call --method scan_volume`, cara resmi & didukung penuh di Android 11-15, dipakai setelah `content delete` saat hapus file. |
| **v1.1.17** | ✅ SELESAI | Upgrade Template Caption: kini bisa UNGGAH FILE (.md/.txt) berisi banyak caption sekaligus — mengatasi UX daftar yang kepanjangan ke bawah kalau caption banyak. Parser `parse_caption_file()` memisah caption per baris kosong, deteksi hashtag otomatis dari baris berawalan `#`, dukung markdown. Endpoint baru: `/captions/upload` (append/replace) & `/captions/all` (hapus semua). UI: tombol "Unggah File" + "Hapus Semua", daftar scrollable. Template default 10 → 28. Disertakan `contoh-caption.md` & `PANDUAN-FILE-CAPTION.md`. |
| **v1.1.18** | ✅ SELESAI | Template caption default DIPERBANYAK dari 28 → 120, dikelompokkan 12 tema psikologi & perilaku konsumen. Divalidasi 0 duplikat & 0 flag over-claim. Hashtag tetap ≤3 saat generate. |
| **v1.1.19** | ✅ SELESAI | PERBAIKAN REGRESI: push & delete video jadi TIDAK realtime — akar masalah `content call scan_volume` (v1.1.16) memindai SELURUH storage HP, lambat di HP berisi banyak file. Diperbaiki: `delete_file()` kembali ke scan BERTARGET per-file (`content delete` + broadcast file spesifik). `scan_volume` tak lagi dipakai di alur push/delete. |
| **v1.1.20** | ✅ SELESAI | Fix bug: nama file berkurung `(`/spasi bikin `touch`/scan/`content delete`/`rm` error `syntax error: unexpected '('`. Diperbaiki dgn helper `_sh_quote()` (kutip tunggal POSIX) di SEMUA perintah shell. Terbukti via simulasi shell Android. |
| **v1.1.21** | ✅ **SELESAI** | **FITUR BARU: penanda tanggal dinamis di kalender "Tanggal Jadwal & Batch". Tanggal yang akun terpilih SUDAH pernah upload ditandai HIJAU (titik + tint) supaya tidak terjadi double upload. Penanda MURNI VISUAL — TIDAK memblokir; user tetap bisa pilih tanggal hijau & upload ulang (mis. setelah membatalkan jadwal yang salah). Endpoint baru `GET /api/history/uploaded-dates?account_id=` (daftar tanggal + jumlah video per tanggal, terisolasi per akun) & `DELETE /api/history/uploaded-dates` (hapus catatan tanggal agar penanda bisa di-reset saat jadwal dibatalkan). Penanda auto-refresh setelah tiap video dikonfirmasi & saat ganti akun. Ada legenda warna + kotak info "sudah upload N video" dgn tombol hapus catatan saat tanggal hijau dipilih.** |
| **v1.1.22** | ✅ SELESAI | Path folder video dapat disimpan permanen sebagai default. |
| **v1.23** | ✅ SELESAI | Dashboard baru, statistik dipindahkan, panel ringkas dihapus, split view responsif 40/60, dan Policy default 24. |
| **v1.24** | ✅ SELESAI | Kirim video sekaligus auto-generate caption, tombol selesai menampilkan jam Jadwal Post, dan aksi copy caption disederhanakan. |
| **v1.25** | ✅ SELESAI | Wajib Copy Semua sebelum konfirmasi selesai, penataan ulang tombol workflow, dan panel Upload mengisi lebar utama secara dinamis. |
| **v1.27** | ✅ SELESAI | Hapus badge jumlah akun dan ubah area aplikasi pada Perangkat HP menjadi split layout datar tanpa panel bertumpuk. |
| **v1.28** | ✅ SELESAI | Ringkas label slot aplikasi menjadi Apk Original dan Apk Kloning. |
| **v1.29** | ✅ SELESAI | Bersihkan daftar akun: hapus dot dan penghitung upload, lalu perjelas ukuran teks akun. |
| **v1.30** | ✅ SELESAI | Hapus menu History dan gabungkan Riwayat Upload lengkap ke Dashboard di bawah Statistik Hari Ini. |
| **v1.26** | ✅ SELESAI | Seragamkan ukuran tombol/ikon, ubah slot aplikasi menjadi horizontal, dan rapikan halaman Pengaturan. |

---

## ✅ CHECKPOINT LOG

### v1.32 — Tempel Caption Otomatis ke HP ✅ SELESAI

- Menambahkan tombol **Tempel ke HP** di posisi paling kanan Panel Caption.
- Urutan final: **Generate Ulang**, **Copy Semua**, **Tempel ke HP**.
- Browser mengisi clipboard, backend memfokuskan jendela scrcpy milik HP sesi aktif, menunggu singkat, lalu mengirim `Ctrl+V`.
- Tombol **Selesai - HH:MM** dibuka setelah auto-paste berhasil dijalankan atau Copy Semua digunakan.
- Tidak ada verifikasi balik otomatis; pengguna memeriksa hasil langsung pada layar HP/scrcpy.
- Ubuntu setup memasang `xdotool` dan `wmctrl`; Windows menggunakan komponen bawaan.
- **ZIP:** `v1.32.zip`



### v1.30 — Riwayat Upload Terintegrasi di Dashboard ✅ SELESAI

- Menu **History** di sidebar dihapus agar navigasi lebih ringkas.
- Panel **Riwayat Upload** dipindahkan ke Dashboard, tepat di bawah **Statistik Hari Ini**.
- Filter HP, akun, tanggal, tombol Reset Filter, tabel riwayat, empty state, dan modal detail tetap tersedia penuh.
- Riwayat dimuat otomatis saat Dashboard dibuka dan ikut diperbarui ketika Dashboard di-refresh.
- Layout riwayat dibuat responsif agar filter tetap nyaman pada monitor, laptop, dan layar sempit.
- Asset frontend memakai query versi `v=1.30` untuk mencegah cache browser memuat aset lama.
- **ZIP:** `remote-hp-v1.30.zip`


### v1.29 — Penyempurnaan Daftar Akun ✅ SELESAI

- Dot ungu di setiap akun dihapus.
- Informasi penghitung upload seperti `↑ 7x` dan `↑ 0x` dihapus.
- Nama akun diperbesar dan dipertebal agar lebih mudah dibaca.
- Nama akun panjang tetap aman dengan pemotongan elipsis dan tooltip nama lengkap.
- Asset frontend memakai query versi `v=1.29` untuk mencegah cache browser memuat aset lama.
- **ZIP:** `remote-hp-v1.29.zip`

### v1.28 — Penyederhanaan Label Slot Aplikasi ✅ SELESAI

- Label **Aplikasi Original** di panel Perangkat HP diubah menjadi **Apk Original**.
- Label **Aplikasi Kloning** di panel Perangkat HP diubah menjadi **Apk Kloning**.
- Label backend terkait slot aplikasi ikut diselaraskan agar tampilan dan pesan sistem konsisten.
- Asset frontend memakai query versi `v=1.28` untuk mencegah cache browser memuat aset lama.
- **ZIP:** `remote-hp-v1.28.zip`

### v1.27 — Perangkat HP Lebih Datar dan Ringkas ✅ SELESAI

- Badge jumlah akun di samping tombol Mirror dihapus.
- Aplikasi Original dan Aplikasi Kloning tetap horizontal, tetapi tidak lagi dibungkus panel kecil masing-masing.
- Kedua area memakai split layout datar dengan divider vertikal agar hierarki visual lebih sederhana.
- Baris akun tetap memiliki state hover dan aktif yang jelas.
- Pada layar sangat kecil, layout otomatis berubah menjadi satu kolom.
- Asset frontend memakai query versi `v=1.27` untuk mencegah cache browser memuat aset lama.
- **ZIP:** `remote-hp-v1.27.zip`

### v1.26 — Konsistensi Kontrol, Slot Horizontal, dan Pengaturan Rapi ✅ SELESAI

- Semua tombol teks memakai tinggi, radius, ukuran font, dan padding yang seragam mengikuti tombol **Kirim Video ke HP**.
- Tombol ikon seperti Refresh HP, Mirror, Edit/Hapus caption, Copy Jadwal, navigasi kalender, menu drawer, dan tutup modal memakai ukuran kotak yang sama.
- Ikon menu utama diperbesar dan diseragamkan; tinggi area klik setiap menu juga dibuat konsisten.
- Subpanel **Aplikasi Original** dan **Aplikasi Kloning** pada setiap kartu HP diubah dari vertikal menjadi horizontal dua kolom.
- Tampilan slot tetap adaptif pada monitor, laptop, dan sidebar drawer; teks akun panjang dipotong rapi tanpa merusak layout.
- Halaman Pengaturan dirombak menjadi grid responsif: Template Caption dan Jadwal Default berdampingan, sedangkan Koneksi & Path Sistem memakai form dua kolom.
- Tombol Simpan Pengaturan dan Backup Database ditempatkan pada area aksi halaman; tombol simpan tambahan di bagian bawah tetap tersedia untuk halaman panjang.
- Asset frontend memakai query versi `v=1.26` untuk mencegah cache browser memuat aset lama.
- **ZIP:** `remote-hp-v1.26.zip`

### v1.25 — Workflow Caption Terkunci dan Layout Lebih Padat ✅ SELESAI

- Tombol `Selesai - HH:MM` pada Panel 2 dinonaktifkan sampai tombol `Copy Semua` pada Panel 3 berhasil menyalin caption.
- Regenerate caption mengunci kembali tombol selesai sehingga caption terbaru wajib disalin ulang.
- Tombol `Generate Ulang` ditempatkan di kiri `Copy Semua` pada kanan atas Panel 3.
- Tombol `Kirim Video` dan `Selesai - HH:MM` dipindahkan ke kanan bawah Panel 2.
- Wrapper Upload diperbaiki agar tidak lagi terkena batas `max-width: 860px`, sehingga kartu mengisi lebar panel utama secara responsif.
- Asset frontend memakai query versi `v=1.25` untuk mencegah cache browser memuat aset lama.
- **ZIP:** `remote-hp-v1.25.zip`

### v1.24 — Workflow Kirim Video dan Caption Terpadu ✅ SELESAI

- Klik **Kirim Video** kini otomatis memanggil generator caption setelah push ADB berhasil.
- Jika generator caption gagal, video tetap berstatus terkirim dan UI menampilkan peringatan tanpa membatalkan proses push.
- Tombol konfirmasi hijau menampilkan jam sesuai Jadwal Post untuk video aktif: `Selesai - HH:MM`.
- Tombol **Copy Caption** dan **Copy Hashtag** dihapus; hanya **Copy Semua** yang dipertahankan.
- Asset frontend memakai query versi `v=1.24` untuk mencegah browser memuat JavaScript/CSS lama dari cache.
- **ZIP:** `remote-hp-v1.24.zip`

### v1.23 — Dashboard dan Responsive Split View ✅ SELESAI

- Menu Dashboard baru sebagai halaman awal.
- Panel Statistik Hari Ini dipindahkan dari Upload ke Dashboard.
- Panel Info Akun dan Riwayat Upload ringkas dihapus.
- Split view monitor lebar: sidebar 40% dan panel utama 60%.
- Layout laptop dipadatkan; layar kecil memakai sidebar drawer.
- Default Policy upload diubah dari 5 menjadi 24.
- **ZIP:** `remote-hp-v1.23.zip`

### v1.1.21 — Penanda Tanggal Dinamis di Kalender (Anti Double-Upload) ✅ SELESAI

Permintaan user: di panel "Tanggal Jadwal & Batch", tandai tanggal yang akun
terpilih SUDAH pernah upload (mis. warna hijau), supaya tidak dobel upload.
Tapi JANGAN blokir permanen — kadang user upload untuk besok, ternyata salah,
lalu hapus jadwalnya & upload ulang. Jadi penanda murni VISUAL.

**Backend (`routes/history.py`):**
- `GET /api/history/uploaded-dates?account_id=<id>` — kembalikan daftar
  tanggal (batch_date) unik yang akun itu sudah punya video terupload, plus
  `counts` (jumlah video per tanggal untuk tooltip). Query di-scope ketat per
  `account_id` — tanggal akun lain tidak ikut. Hanya batch_date non-kosong.
- `DELETE /api/history/uploaded-dates` — body `{account_id, date}`. Hapus
  catatan upload (uploaded_videos + upload_sessions) akun tsb pada tanggal
  itu, supaya penanda hijau bisa di-reset saat jadwal dibatalkan. Hanya
  menghapus CATATAN di DB aplikasi — tidak menyentuh HP/TikTok Studio.

**Frontend (`static/upload.js`, `static/app.js`, `static/style.css`):**
- State baru `Upload.uploadedDates` (map tanggal→jumlah) &
  `uploadedDatesAccountId` (deteksi data basi saat ganti akun).
- `loadUploadedDates(force)` — fetch tanggal untuk akun terpilih, dgn guard
  anti-fetch-ganda & anti-race (cek akun belum berganti saat respons tiba),
  lalu render ulang kalender + updateDateUI.
- `renderCalendar()` menambahkan kelas `has-upload` + titik hijau
  `.cal-upload-dot` pada sel tanggal yang ada di uploadedDates, dengan
  tooltip jumlah video. Tetap bisa diklik (tidak diblokir).
- Auto-refresh penanda: dipanggil saat panel upload dirender, setiap video
  dikonfirmasi (`confirmCurrentVideo`), setelah selesai sesi, dan saat ganti
  akun (`Upload.reset()` mengosongkan penanda lama).
- `updateDateUI()` menampilkan kotak info "● Sudah upload N video di tanggal
  ini" + tombol "🗑️ Hapus catatan tanggal ini" HANYA saat tanggal terpilih
  memang sudah ada upload. Tombol memanggil `confirmClearDateRecord()`.
- Legenda warna hijau ditambahkan di bawah keterangan tanggal.
- `API.del()` di-upgrade agar bisa mengirim body JSON (backward-compatible).
- CSS: `.cal-cell.has-upload` (tint + border hijau), `.cal-upload-dot` (titik
  hijau pojok kanan-bawah), penyesuaian agar tetap kontras saat sel juga
  `today`/`selected` (sel terpilih tetap biru aksen + titik putih).

- [x] **Teruji:**
  - Endpoint uploaded-dates: per-akun terisolasi, counts benar, akun tanpa
    histori → kosong, tanpa account_id → 400. (HTTP)
  - Integrasi upload nyata: sebelum upload kosong → setelah upload tanggalnya
    muncul dgn count benar → upload ulang di tanggal sama TIDAK diblokir.
  - Endpoint hapus catatan tanggal: menghapus video+sesi tanggal itu, tanggal
    hilang dari daftar, validasi param 400. (HTTP)
  - Logika renderCalendar (Node): tanggal ber-upload dcapat `has-upload` +
    titik; tanggal lain polos; sel hari-ini+upload digabung benar.
  - Logika updateDateUI (Node): tombol hapus muncul hanya saat tanggal
    terpilih ada upload, kosong bila tidak.
  - Regresi penuh: 120 caption, slot akun, upload caption, stats, boot,
    keseimbangan div HTML — semua normal.
- [x] **ZIP:** `remote-hp-v1.1.21.zip`

---

### v1.1.20 — Fix Bug: Nama File Berkurung/Spasi Bikin Shell Android Error ✅ SELESAI

Dari log user (screenshot): file bernama `grok-video-...efdf9 (1).mp4` — yang
mengandung tanda kurung `(` `)` dan spasi — memicu error berulang:
```
! Gagal update tanggal file: /system/bin/sh: syntax error: unexpected '('
! Media scan gagal: /system/bin/sh: syntax error: unexpected '('
```
File dengan nama biasa (tanpa kurung) berhasil; hanya yang berkurung gagal.

**Akar masalah:** pada `adb shell <cmd>`, semua argumen setelah "shell"
digabung ADB jadi satu string, lalu dijalankan ulang oleh `/system/bin/sh` DI
HP. Karakter yang punya arti khusus di shell — kurung `()`, spasi, `&`, `;`,
`'`, `"`, `*`, `$` — ditafsirkan shell alih-alih jadi bagian nama file,
sehingga `sh` error. Ini mempengaruhi SEMUA perintah shell yang memuat path:
`touch`, `am broadcast` (media scan), `content delete`, `rm`, `mkdir`, `ls`.
(Push file sendiri via `adb push` tidak kena, karena adb menangani argumennya
tanpa lewat shell.)

**Perbaikan (`services/adb.py`):**
- Helper baru `_sh_quote(path)`: membungkus path dalam kutip tunggal POSIX
  yang aman untuk shell mana pun. Tiap kutip tunggal di dalam path di-escape
  jadi `'\''` (pola standar POSIX), jadi bahkan nama file seperti
  `it's a file.mp4` pun aman.
- Diterapkan ke SEMUA perintah shell yang memuat path/argumen berisiko:
  - `touch_file_now()`: `touch _sh_quote(path)`
  - `scan_media()`: `-d _sh_quote("file://" + path)`
  - `delete_file()`: `rm -f _sh_quote(path)` dan `content delete --where
    _sh_quote("_data='<escaped>'")` (quoting berlapis: kutip tunggal SQL di
    dalam untuk MediaStore, dibungkus _sh_quote untuk shell Android).
  - `ensure_target_dir()`: `mkdir -p _sh_quote(target_dir)`
  - `list_remote_files()`: `ls -1 _sh_quote(target_dir)`

- [x] **Teruji:**
  - `_sh_quote` diverifikasi lewat shell POSIX sungguhan: untuk 5 nama
    bermasalah (kurung, spasi, `&;`, kutip tunggal, normal) — hasil quote,
    saat dieksekusi shell, mengembalikan path asli PERSIS.
  - Dibuat fake ADB yang MENSIMULASIKAN shell Android sungguhan (menjalankan
    argumen shell lewat `sh -c`). Terbukti: kode LAMA (tanpa quote) untuk
    file berkurung menghasilkan `Syntax error: "(" unexpected` PERSIS seperti
    error user; kode BARU berhasil tanpa error.
  - Integrasi HTTP penuh: upload folder berisi file bernama
    `grok-video (1).mp4` DAN `normal-video.mp4` — keduanya push & delete
    100% tanpa warning/error.
  - Regresi: 120 caption, slot akun, upload caption, boot — semua normal.
- [x] **Catatan soal kecepatan push:** kelambatan transfer file saat push
  sebagian besar wajar (tergantung ukuran file & kecepatan USB HP), tidak
  bisa dipercepat dari sisi aplikasi. Yang sempat memperlambat tidak wajar
  (scan_volume seluruh storage) sudah dihapus di v1.1.19. Operasi tambahan
  saat push (touch + media scan 1 file) bersifat instan.
- [x] **ZIP:** `remote-hp-v1.1.20.zip`

---

### v1.1.19 — Perbaikan Regresi: Push & Delete Tidak Realtime Lagi (scan_volume Terlalu Berat) ✅ SELESAI

User melaporkan: setelah v1.1.16-18, push & delete video ke HP jadi TIDAK
realtime lagi — galeri baru ke-update setelah aplikasi ditutup-buka berkali-
kali. Ini regresi dari perbaikan galeri sebelumnya.

**Akar masalah:** `content call --method scan_volume --arg external_primary`
yang ditambahkan di v1.1.16 (untuk memperbaiki refresh galeri saat delete)
ternyata memindai **SELURUH storage HP** — semua foto, video, musik, dokumen,
bukan cuma folder RemoteHP. Dikonfirmasi lewat riset dokumentasi:
"scan_volume scans the entire external primary storage". Di HP yang berisi
banyak file (galeri penuh), scan menyeluruh ini makan waktu lama (belasan
detik s/d menit). Galeri baru ke-update setelah scan raksasa itu kelar —
persis gejala "harus tutup-buka aplikasi berkali-kali". Lebih buruk lagi,
scan berat yang masih jalan di background juga membuat operasi push
BERIKUTNYA terasa lambat karena antri di belakang scan tersebut.

Ini ironisnya kebalikan dari maksud awal: v1.1.16 mengira scan_volume lebih
andal (karena broadcast folder deprecated), padahal untuk perubahan 1 file,
yang tepat justru scan BERTARGET. Riset menegaskan: "full-volume scans are
ideal for bulk updates; file-specific scans are ideal for small, targeted
changes".

**Perbaikan (`services/adb.py`):**
- `delete_file()` dikembalikan ke pendekatan scan bertarget yang cepat &
  hanya menyentuh 1 entri/1 file:
  1. `content delete --where "_data='<path>'"` — menghapus TEPAT 1 baris
     entri file itu dari MediaStore (instan, cuma 1 baris DB).
  2. Broadcast `MEDIA_SCANNER_SCAN_FILE` ke path file spesifik itu saja
     (ringan, bukan folder/volume).
  - `scan_volume`/`rescan_volume()` TIDAK lagi dipanggil di sini.
- `push_file()` tetap seperti semula (sudah ringan sejak awal): `touch` +
  broadcast scan file spesifik. Tidak pernah pakai scan_volume — jadi begitu
  delete tidak lagi memicu scan berat di background, push pun kembali
  realtime.
- Fungsi `rescan_volume()` dipertahankan di kode TAPI diberi peringatan jelas
  bahwa ia sengaja tidak dipakai di alur push/delete (hanya utilitas cadangan
  bila perlu rescan menyeluruh manual).
- `routes/upload.py`: log delete kembali mengikuti `mediastore_clean_ok`
  (hapus entri DB) alih-alih `rescan_ok`.

- [x] **Teruji (fake ADB, karena sandbox tak punya Android fisik untuk
  mengukur kecepatan galeri sungguhan):**
  - DELETE: dipastikan urutan `rm` → `content delete` → broadcast file
    spesifik, dan TIDAK ada lagi panggilan `scan_volume`.
  - PUSH: dipastikan `touch` → broadcast file spesifik, tanpa `scan_volume`.
  - Integrasi HTTP `/push` & `/confirm`: log benar, kedua operasi ringan.
  - Regresi: 120 caption default, slot akun, boot — semua normal.
  - **Catatan jujur:** perbaikan berdasarkan analisis + dokumentasi resmi soal
    perilaku scan_volume (memindai seluruh storage) vs scan bertarget.
    Sandbox tak bisa mengukur kecepatan galeri di HP fisik — mohon
    dikonfirmasi lagi di HP setelah update ini.
- [x] **ZIP:** `remote-hp-v1.1.19.zip`

---

### v1.1.18 — Template Caption Default Diperbanyak 28 → 120 ✅ SELESAI

Permintaan user: perbanyak template caption default sebanyak mungkin dalam 1
sesi (100+ boleh). Ditambah dari 28 menjadi **120 caption**, semua tetap
berfokus pada psikologi & perilaku konsumen — tanpa memuji produk / tanpa
over-claim / tanpa ajakan beli langsung.

**12 tema caption** (masing-masing ~10, ditulis manual agar natural &
bervariasi, bukan template-isian kaku):
1. Kebiasaan scroll & lapar mata
2. Menimbang keputusan / mindful (jeda sebelum beli)
3. Timing, mood, kondisi (capek/bosen/gajian)
4. Efek harga, diskon, angka (psikologi angka 9, gratis ongkir, bundling)
5. FOMO, sosial, tren (ikut penasaran, rekomendasi)
6. Nilai, kepuasan, hubungan dengan barang
7. Pertanyaan ke audiens (engagement)
8. Refleksi & catatan harian (nyatet pengeluaran, pola diri)
9. Kebiasaan keranjang, wishlist
10. Perbandingan & riset (secukupnya, hindari overthinking)
11. Pengendalian diri & kebiasaan sehat (jeda 24 jam, budget senang-senang)
12. Ringan, relatable, penutup

**Validasi otomatis sebelum ditulis:**
- 0 duplikat konten (dicek via set).
- 0 flag over-claim. 6 caption awalnya false-positive karena mengandung kata
  "diskon"/"checkout"/"promo"/"terbaik"/"langsung beli" dalam konteks NETRAL
  (justru sedang membahas perilaku, bukan mengajak) → keenamnya di-reword
  (mis. "diskon gede" → "potongan harga gede", "checkout-nya nggak jadi" →
  "ujungnya nggak jadi lanjut", "notifikasi promo" → "notifikasi penawaran",
  "keputusan terbaik" → "keputusan paling pas") sampai seluruh 120 lolos
  `flag_risky_caption()` dengan 0 flag.
- Hashtag tiap caption ≤3 token (dan tetap dibatasi 3 saat generate).

Implementasi: blok `samples` di `database/db.py` (fungsi `_seed_defaults()`)
diganti dari 28 → 120 entri. Hanya berlaku untuk DB baru (seed saat kosong);
DB lama user tidak tersentuh — kalau mau memakai daftar baru ini, bisa lewat
fitur "Unggah File" (mode replace) atau mulai dari DB bersih.

- [x] **Teruji (otomatis):**
  - Seed DB baru menghasilkan tepat 120 caption; 0 duplikat & 0 flag
    over-claim diverifikasi ulang setelah masuk DB.
  - Hashtag ≤3 saat generate.
  - Regresi: fitur Unggah File (append/replace), Hapus Semua, slot akun,
    boot penuh — semua tetap normal.
- [x] **ZIP:** `remote-hp-v1.1.18.zip`

---

### v1.1.17 — Upgrade Template Caption: Unggah File + Perbanyak Default ✅ SELESAI

Permintaan user: daftar Template Caption jadi kepanjangan ke bawah kalau diisi
banyak (UX buruk). Solusi: bisa unggah file .md/.txt berisi banyak caption
sekaligus, plus perbanyak template default.

**Parser (`services/caption.py` → `parse_caption_file()`):**
- Memisah file jadi caption per BLOK (dipisah baris kosong atau garis `---`).
- Baris berawalan `#`/`＃` yang mayoritas tokennya hashtag → dianggap baris
  HASHTAG (dibedakan dari heading markdown `# Judul` lewat
  `_looks_like_hashtag_line()` yang cek proporsi token hashtag).
- `_clean_content_line()` membersihkan penanda markdown di awal baris
  (heading, bullet `-`/`*`/`+`, penomoran `1.`, quote `>`).
- Blok yang hanya berisi 1 baris heading markdown (kemungkinan JUDUL dokumen)
  dilewati otomatis, supaya judul file tidak ikut jadi caption.
- Normalisasi hashtag: `＃`→`#`, buang duplikat case-insensitive.

**Endpoint baru (`routes/settings.py`):**
- `POST /api/settings/captions/upload` — body `{text, mode}`. mode `append`
  (tambah) atau `replace` (hapus semua dulu, lalu isi). Batas 1 MB / 1000
  caption. Return ringkasan: added, skipped_empty, replaced, risky_count.
- `DELETE /api/settings/captions/all` — hapus semua caption sekaligus.

**UI (`templates/index.html` + `static/app.js`):**
- Kartu Template Caption: tombol "📄 Unggah File" & "🗑️ Hapus Semua" +
  label jumlah caption. Daftar dibungkus wadah scrollable (max-height 340px)
  supaya tidak memanjang ke bawah tak terbatas.
- Modal unggah: pilih file → baca via `File.text()` di browser → kirim
  teksnya ke endpoint. Ada pratinjau perkiraan jumlah caption, pilihan mode
  append/replace, dan peringatan bila ada caption ter-flag over-claim.
- Modal.open() ditambah dukungan properti `id` pada footerButtons (kecil,
  backward-compatible) supaya tombol submit bisa di-disable saat proses.

**Template default (`database/db.py`):** diperbanyak dari 10 → 28 caption,
semua berfokus pada psikologi/perilaku konsumen (kebiasaan scroll, menimbang
keputusan, mood belanja, efek harga/kelangkaan) — TIDAK memuji produk / tidak
mengajak beli langsung. 4 caption sempat ter-flag false-positive oleh
validator (kata "checkout"/"diskon"/"nagih" dalam konteks netral) → di-reword
agar seluruh 28 caption lolos `flag_risky_caption()` dengan 0 flag.

**File tambahan dalam paket:** `contoh-caption.md` (10 caption siap pakai,
murni caption tanpa teks instruksi agar bisa langsung diunggah utuh) &
`PANDUAN-FILE-CAPTION.md` (penjelasan format).

- [x] **Teruji (otomatis):**
  - Parser: 7 skenario (baris kosong + hashtag terpisah, markdown
    heading/bullet/`---`, tanpa hashtag, caption multi-baris, file kosong,
    `＃` fullwidth + duplikat, judul dokumen dilewati) — semua benar.
  - Endpoint upload (append & replace), hapus semua, + validasi error (file
    kosong, cuma hashtag) — via HTTP, LULUS.
  - Integrasi penuh: CRUD caption lama (tambah/edit/hapus/check risky) TETAP
    jalan berdampingan dengan fitur upload baru; generate caption pasca-upload
    normal.
  - 28 caption default diverifikasi: jumlah tepat 28 & seluruhnya 0 flag
    over-claim; hashtag tetap dibatasi ≤3 saat generate.
  - `contoh-caption.md` diverifikasi menghasilkan tepat 10 caption bersih.
  - Semua ID statis caption baru dikonfirmasi ada di HTML; regresi slot akun
    & caption generator normal; boot penuh OK.
- [x] **ZIP:** `remote-hp-v1.1.17.zip`

---

### v1.1.16 — Patch: Galeri Masih Belum Refresh Realtime Setelah Hapus (Deprecated API) ✅ SELESAI

User melaporkan setelah v1.1.15: push sudah realtime muncul di Galeri (fix
tanggal berhasil), tapi hapus **masih belum** realtime — observasi tajam
user: "seperti refresh terlalu cepat, delete belum 100% selesai sudah
refresh". Setelah diperiksa ulang, ternyata bukan soal timing/race condition
(kode Python sudah sequential & blocking dengan benar), melainkan **cara
memberi tahu galeri berbeda antara push vs delete**:

- Saat **push**: broadcast scan ke **file yang memang ADA** — jalur paling
  reliable, scanner langsung memproses & galeri (termasuk galeri bawaan
  Xiaomi/HyperOS yang cenderung pelit refresh) langsung dengar eventnya.
- Saat **delete** (v1.1.15): hanya `content delete` (hapus baris DB) +
  broadcast scan ke file yang **sudah tidak ada**. Diriset lebih lanjut:
  broadcast `MEDIA_SCANNER_SCAN_FILE` ke path (apalagi FOLDER) **sudah
  DEPRECATED sejak Android 9 (API 29)** — Google secara resmi menyatakan
  "Callers should migrate to inserting items directly into MediaStore" —
  sehingga tidak lagi reliable dipakai untuk memicu refresh di Android
  modern (yang kemungkinan besar dijalankan Redmi 14C user).

**Perbaikan (`services/adb.py`):**
- Fungsi baru `rescan_volume()`: menjalankan
  `adb shell content call --uri content://media --method scan_volume --arg
  external_primary` — cara **resmi & didukung penuh** di Android 11-15
  untuk memaksa MediaStore rescan SELURUH volume storage utama, dikonfirmasi
  lewat riset sbg pendekatan paling andal di Android modern (berbeda dari
  broadcast scan folder/file yang sudah deprecated).
- `delete_file()` diperbarui: setelah `content delete` (hapus baris DB),
  panggil `rescan_volume()` sbg jalur refresh UTAMA — broadcast scan ke file
  spesifik tetap dipertahankan sbg fallback tambahan (harmless, masih
  berfungsi di sebagian vendor/versi meski deprecated).
- `routes/upload.py`: log "Galeri di-refresh" sekarang mengikuti hasil
  `rescan_ok` (bukan `mediastore_clean_ok` seperti sebelumnya).

- [x] **Teruji (fake ADB, karena sandbox tak punya Android fisik untuk
  memverifikasi kecepatan refresh galeri sungguhan):**
  - Urutan panggilan `rm` → `content delete` → `content call scan_volume` →
    broadcast fallback dipastikan benar & lengkap.
  - Command `scan_volume` diverifikasi PERSIS sesuai command resmi yang
    didokumentasikan untuk Android modern.
  - Integrasi HTTP penuh (`/push` → `/confirm`) memverifikasi baris log
    "Galeri di-refresh" muncul dengan benar mengikuti `rescan_ok`.
  - Regresi: push (touch + scan) tetap normal tidak terganggu; slot akun &
    caption generator tetap normal.
  - **Catatan jujur:** perbaikan ini didasarkan pada riset & dokumentasi
    resmi Android soal API mana yang deprecated vs yang didukung penuh —
    sandbox tidak bisa mengukur kecepatan refresh galeri sungguhan di HP
    fisik. Mohon dikonfirmasi lagi di Redmi 14C setelah update ini.
- [x] **ZIP:** `remote-hp-v1.1.16.zip`

---

### v1.1.15 — Fix Galeri: Hapus Tidak Refresh & Urutan Tanggal Video ✅ SELESAI

Dua masalah dilaporkan user dari fitur Upload (setelah screenshot menunjukkan
konsol push/delete normal, tapi perilaku di Galeri HP tidak sesuai harapan):

**1. Video yang dihapus dari HP masih nyangkut/tampil di Galeri**

Akar masalah: `delete_file()` hanya menjalankan `rm -f` di filesystem HP —
tidak pernah memberi tahu **MediaStore** (basis data yang dipakai aplikasi
Galeri, terpisah dari filesystem). Tanpa pemberitahuan, MediaStore tetap
menyimpan entri lama sampai ada media scan penuh (mis. HP di-restart),
sehingga file yang sudah dihapus masih terlihat/thumbnail rusak di Galeri.

- `services/adb.py` → `delete_file()`: setelah `rm` sukses, tambah 2 langkah:
  1. **`adb shell content delete --uri content://media/external/file --where
     "_data='<path>'"`** — hapus entri MediaStore langsung via
     ContentProvider (cara paling andal, Android 7+/API 24+).
  2. Broadcast `MEDIA_SCANNER_SCAN_FILE` ke path yang sudah dihapus sbg
     fallback tambahan (aman, tidak error meski langkah 1 sudah berhasil).
- **Bug quoting ditemukan & diperbaiki SEBELUM rilis** saat pengujian: karena
  argumen `adb shell` digabung ADB CLIENT lalu dijalankan oleh shell DI
  ANDROID (bukan shell lokal PC), tanda kutip tunggal polos `'...'` akan
  DILUCUTI shell Android sebelum sampai ke `content`, membuat klausa SQL-nya
  kehilangan kutipnya (tidak valid). Diperbaiki dengan membungkus seluruh
  klausa dalam kutip GANDA (`"_data='...'"`) supaya shell Android hanya
  melucuti kutip ganda pembungkus & mempertahankan kutip tunggal SQL di
  dalamnya sebagai karakter literal. Ditambah `_sql_escape()` (escape kutip
  tunggal ala SQL) untuk nama file edge-case yang mengandung kutip tunggal.
- `routes/upload.py` → endpoint `/confirm`: baris log baru "Galeri di-refresh"
  ditambahkan ke konsol saat pembersihan MediaStore berhasil.

**2. Video dengan tanggal file lama tampil di urutan BAWAH Galeri**

Akar masalah: `adb push` **mempertahankan** tanggal modifikasi file sumber di
PC. Kalau video dibuat/diedit beberapa hari lalu (mis. tanggal 9) lalu baru
di-push hari ini (tanggal 12), MediaStore mencatatnya dengan tanggal LAMA →
Galeri (yang umumnya urut berdasarkan tanggal terbaru) menampilkannya di
bawah, bukan di atas.

- `services/adb.py` → fungsi baru `touch_file_now()`: menjalankan
  `adb shell touch <remote_path>` **di HP** (bukan mengubah file asli di PC
  sama sekali) tepat setelah push sukses dan SEBELUM media scan — supaya
  tanggal modifikasi yang dibaca MediaStore saat scan adalah waktu SEKARANG,
  membuat video otomatis tampil di **urutan paling atas/terbaru**.
- `push_file()` diperbarui: urutan sekarang push → `touch_file_now()` →
  `scan_media()` (touch harus sebelum scan, supaya scan membaca tanggal yang
  sudah di-update).
- `routes/upload.py` → endpoint `/push`: baris log baru "Tanggal file
  di-update ke sekarang" ditambahkan ke konsol.

- [x] **Teruji (otomatis, fake ADB karena sandbox tak punya Android fisik):**
  - `push_file()`: urutan panggilan `push` → `touch` → `am broadcast` benar;
    kedua flag `touch_ok`/`media_scan_ok` ter-set dengan tepat.
  - `delete_file()`: urutan panggilan `rm` → `content delete` → `am
    broadcast` benar; where-clause SQL terverifikasi PERSIS
    `"_data='/path'"` (kutip ganda pembungkus + kutip tunggal SQL utuh) —
    bug quoting awal (kutip tunggal polos yang akan dilucuti shell Android)
    ditemukan & diperbaiki lewat pengujian ini SEBELUM dirilis.
  - Escape SQL untuk nama file yang (secara ekstrem) mengandung kutip
    tunggal diverifikasi terpisah (`video's_test.mp4` → `video''s_test.mp4`).
  - Integrasi HTTP penuh (`/api/upload/start` → `/push` → `/confirm`)
    memverifikasi kedua baris log baru muncul dengan benar di konsol yang
    dilihat user.
  - Regresi fitur lain (slot akun batas 8, caption generator) tetap normal.
- [x] **ZIP:** `remote-hp-v1.1.15.zip`

---

### v1.1.14 — Fitur Workflow Dihapus Total (Batasan Fundamental scrcpy vs ADB) ✅ SELESAI

Setelah patch v1.1.13 (fix PTY `-tt`), user melaporkan: mirror scrcpy jalan
normal, capture ADB terbukti BISA merekam (6 langkah terekam via tombol
manual Back/Enter/Rekam Teks), TAPI **tap/swipe langsung di jendela mirror
scrcpy tetap 0 langkah terekam**. Diriset lebih lanjut — dan ini akhirnya
terungkap sebagai **batasan fundamental**, bukan bug yang bisa ditambal:

**Akar masalah:** scrcpy **tidak** menyentuh layar secara fisik. Saat user
klik di jendela mirror, scrcpy **menyuntikkan (inject)** event langsung lewat
Android `InputManager` (API level tinggi) — jalur software yang SEPENUHNYA
terpisah dari device sentuh fisik (`/dev/input/eventN`) yang didengarkan
`getevent`. Karena Android sendiri yang memprosesnya di level atas, HP tetap
merespons secara visual (aplikasi terbuka, layar bereaksi) — tapi
`getevent` di device fisik **tidak pernah melihat sentuhan itu**, sehingga
mustahil direkam lewat pendekatan `getevent`, berapa pun perbaikan teknis
yang dicoba (dikonfirmasi lewat riset dokumentasi scrcpy/Android
`InputDispatcher`, yang menyebut event injeksi diberi `device id = -1`,
berbeda total dari event sentuhan fisik).

Diberikan 2 opsi solusi (rekam pakai jari fisik langsung tanpa lewat scrcpy,
atau tangkap event scrcpy itu sendiri lewat cara berbeda) — **user memilih
menghapus fitur ini sampai ke akarnya**, karena kompromi apa pun terasa tidak
sepadan dengan kerumitan tambahan yang diperlukan.

**Dihapus total:**
- File: `services/recorder.py`, `routes/workflow.py`, `static/workflow.js`,
  folder `scripts/` (skrip hasil rekam).
- `app.py`: import & registrasi `workflow_bp` dihapus.
- `templates/index.html`: menu "Workflow" di sidebar, seluruh halaman
  `page-workflow`, kartu "Jeda Acak Antar-Langkah Workflow" di Pengaturan,
  tag `<script src="/static/workflow.js">` — semua dihapus.
- `static/app.js`: pemanggilan `initWorkflowPage()`, load/save setting
  `setStepDelayMin`/`setStepDelayMax` dihapus.
- `database/schema.sql`: tabel `workflow_runs` + 2 index terkait dihapus dari
  definisi skema (instalasi baru tidak akan membuatnya lagi).
- `database/db.py`: setting default `step_delay_min_ms`/`step_delay_max_ms`/
  `workflow_capture_elements_default` dihapus dari `_seed_defaults()`.
  Ditambah `_migrate_remove_workflow_feature()` — migrasi baru yang
  **otomatis membersihkan DB LAMA milik user** yang sempat menjalankan
  v1.1.12/v1.1.13: `DROP TABLE workflow_runs` + hapus 3 setting di atas.
  Idempotent, aman dipanggil berkali-kali.
- `setup-windows.bat` & `setup-ubuntu.sh`: catatan penutup "Fitur Workflow
  Otomatisasi" dihapus; header komentar disesuaikan (scrcpy kini murni untuk
  Mirror saja).
- `.gitignore`: entri folder `scripts/` dihapus.
- `static/style.css`: blok CSS `.wf-vars`/`.wf-vars-body` (sudah mati, tak
  dipakai di mana pun) dihapus; komentar yang menyebut "Workflow" pada CSS
  yang MASIH dipakai fitur lain (`.tag-yellow` dsb untuk status device)
  diperbaiki tanpa menghapus class-nya.

**Tidak diubah / tetap utuh:** fitur Upload (FIFO), Mirror scrcpy (murni
untuk melihat HP), History, Caption Generator, Jadwal Generator, Slot Akun
Original/Kloning, Guard Duplikasi — semua tidak tersentuh oleh perombakan ini.

- [x] **Teruji (otomatis):**
  - Endpoint `/api/workflow/*` dipastikan benar-benar hilang dari
    `app.url_map` & mengembalikan 404.
  - Migrasi `_migrate_remove_workflow_feature()`: DB lama simulasi dengan
    tabel `workflow_runs` + 3 setting terkait → semuanya bersih total setelah
    `init_db()`, idempotent.
  - Boot penuh + regresi semua fitur lain (slot batas 8, caption regen ≤3
    hashtag, settings CRUD) — semua LULUS, tidak ada regresi.
  - Pemindaian menyeluruh kode (`grep -rin "workflow\|maestro"`) memastikan
    tidak ada sisa kode fungsional; hanya tersisa istilah umum "workflow"
    (alur kerja upload — fitur BERBEDA yang memang masih ada) dan kode
    migrasi pembersihan yang sengaja tetap menyebut nama lama untuk
    keperluan cleanup DB.
  - `setup-windows.bat`/`setup-ubuntu.sh`: sintaks & CRLF diverifikasi ulang
    valid setelah pembersihan.
- [x] **ZIP:** `remote-hp-v1.1.14.zip`

---

### v1.1.13 — Patch Krusial: Rekam ADB 0 Langkah di HP Nyata (Buffer PTY) ✅ SELESAI

Dilaporkan user langsung setelah v1.1.12: mirror scrcpy jalan normal, status
"Sedang Merekam" muncul, tapi setelah 24 detik beraktivitas nyata di HP asli
(Redmi 14C), hasilnya **0 langkah terekam**. Diagnosis via log `adb shell
getevent -lp` yang diminta dari user menunjukkan device sentuh (`fts_ts`,
`/dev/input/event3`) terdeteksi BENAR dengan format standar (`BTN_TOUCH` +
`ABS_MT_POSITION_X/Y` + `ABS_MT_SLOT`/`ABS_MT_TRACKING_ID`) — jadi bukan
soal parsing format event.

**Akar masalah sesungguhnya:** saat `adb shell getevent ...` dipanggil secara
NON-INTERAKTIF (dari program lewat `subprocess.Popen`, bukan dari terminal
manusia), sisi Android menganggap stdout-nya BUKAN layar interaktif (TTY) —
sehingga proses `getevent` di Android **menahan outputnya di buffer internal**
alih-alih mengirim tiap event langsung. Karena sentuhan manusia hanya
menghasilkan sedikit data (jauh dari ukuran buffer penuh), data itu **tidak
pernah ter-flush**, dan begitu proses dihentikan (`proc.terminate()` saat
"Stop & Tinjau" diklik), seluruh buffer yang belum terkirim **hilang total**.
Ini persis cocok dengan gejala: aktif lama, tapi 0 langkah.

**Perbaikan (`services/recorder.py`):**
- `start_recording()`: command diubah dari `adb shell getevent -lt <path>`
  menjadi **`adb shell -tt getevent -lt <path>`**. Flag `-tt` memaksa ADB
  mengalokasikan pseudo-terminal (PTY) meski dipanggil non-interaktif,
  sehingga Android menganggap ada "layar" yang mendengarkan dan mengirim
  output secara langsung per baris, bukan menahannya di buffer.
- Parsing baris diperbarui untuk membuang `\r` selain `\n` (`rstrip("\r\n")`),
  mengantisipasi mode PTY yang bisa mengakhiri baris dengan `\r\n`.
- `subprocess.Popen` diberi `bufsize=1` (line-buffered di sisi Python) sebagai
  lapisan tambahan, meski perbaikan utama tetap di sisi Android (`-tt`).

**UI (`static/workflow.js`):** ditambahkan peringatan dini di kartu "Sedang
Merekam" — kalau sudah lebih dari 8 detik berjalan tapi 0 langkah terdeteksi,
tampil kotak info yang mengingatkan user untuk memastikan benar-benar
menyentuh HP, sehingga masalah (kalau masih terjadi di device lain) diketahui
lebih awal daripada menunggu sampai "Stop & Tinjau" baru sadar kosong.

- [x] **Teruji (fake ADB, karena sandbox tak punya Android fisik untuk
  memverifikasi efek PTY-vs-buffer secara langsung):**
  - Command construction memuat `-tt` dengan benar & tidak merusak parsing
    argumen adb yang sudah ada.
  - Regresi penuh alur rekam→olah→simpan→eksekusi tetap LULUS dengan
    perubahan command & parsing baris baru.
  - Boot aplikasi normal.
  - **Catatan jujur:** karena sandbox tidak bisa mensimulasikan perbedaan
    perilaku buffer PTY-vs-pipe di Android sungguhan, perbaikan ini divalidasi
    berdasarkan pemahaman teknis akar masalah (dikonfirmasi lewat log asli
    user) + praktik umum yang terdokumentasi luas untuk kasus serupa
    (`getevent`/`logcat` yang "tidak real-time" saat dipipe). Perlu
    dikonfirmasi ulang oleh user di HP asli.
- [x] **ZIP:** `remote-hp-v1.1.13.zip`

---

### v1.1.12 — Maestro Dihapus Total, Diganti Perekam Workflow Berbasis ADB Murni ✅ SELESAI

Perombakan besar atas permintaan eksplisit user, setelah diskusi panjang
membandingkan alternatif (Maestro, Appium, aplikasi Android seperti Auto.js/
AutoJs6, `getevent`/`sendevent` ADB murni). Keputusan akhir: **ADB murni**,
karena satu-satunya opsi yang (a) tidak perlu instalasi apa pun selain ADB
yang sudah wajib ada, (b) tidak perlu app tambahan di tiap HP, (c) cocok
persis dengan alur yang diinginkan user — mirror di PC (scrcpy) lalu rekam
otomatis di background.

**Cara eksekusi (dijelaskan ke user sebelum implementasi):** koordinat sebagai
andalan utama (karena TikTok bukan aplikasi sendiri, elemen UI-nya tak stabil
diakses dari luar — Maestro/Appium pun pada praktiknya sering jatuh ke
koordinat juga untuk app pihak ketiga), DENGAN fallback opsional deteksi
elemen via `uiautomator dump` (dicoba dulu saat replay; kalau elemen tak
ketemu, otomatis jatuh ke koordinat asli).

**`services/recorder.py`** (baru, pengganti total `services/maestro.py` yang
dihapus):
- **Rekam:** `start_recording()` mendeteksi device layar sentuh via
  `adb shell getevent -lp` (ambil path device + rentang koordinat mentah),
  ambil resolusi layar via `adb shell wm size`, lalu jalankan
  `adb shell getevent -lt <device>` di thread background. Setiap sentuhan
  (BTN_TOUCH DOWN→UP) dikumpulkan sbg 1 "stroke" dg koordinat & waktu.
- **Olah jadi langkah bersih:** `_build_steps()` mengelompokkan stroke
  berurutan waktu; jarak ≤24px → **tap** (atau **tekan-lama** jika ≥500ms),
  jarak lebih jauh → **swipe**. Koordinat mentah dinormalisasi ke pixel layar
  via `_scale_coord()`. Jeda antar-langkah dihitung dari selisih waktu asli
  (dibatasi maks 4 detik agar jeda-mikir-lama saat rekam tak ikut kebawa).
- **Ketik teks 100% akurat:** BUKAN ditebak dari event mentah (rapuh) —
  `add_manual_text_step()` dipanggil dari tombol "Rekam Teks" di UI (user
  ketik di form Remote HP, bukan keyboard HP), jadi tertangkap persis.
  `add_manual_key_step()` untuk tombol khusus (Back/Home/Enter/Recent Apps).
- **Deteksi elemen (opsional, best-effort):** kalau diaktifkan, tiap tap
  memicu `_attach_element_hint()` di thread terpisah (tak menghambat capture)
  yang menjalankan `uiautomator dump` + `_find_element_at_point()` (cari node
  XML dg bounds terkecil yang memuat titik tap), simpan text/resource-id/
  content-desc sbg petunjuk.
- **Skrip tersimpan:** file `.json` di folder `scripts/` (`list_scripts()`,
  `load_script()`, `save_script()`, `delete_script()`, `rename_script()`) —
  polanya disalin dari cara `flows/` Maestro dulu mengelola file `.yaml`,
  disesuaikan untuk JSON.
- **Eksekusi:** `start_run()`/`_run_worker()` mengeksekusi tiap langkah via
  `adb shell input tap/swipe/text/keyevent`, dengan jeda tercatat +
  `random_extra_delay_ms()` (setting baru `step_delay_min_ms`/`max_ms`,
  default **300–1200ms** — kecil karena berlaku PER LANGKAH, beda dari
  DELAY_MS Maestro dulu yang 1x per seluruh eksekusi). Mendukung step
  `text_var` (mis. `CAPTION`) yang nilainya diisi ulang saat menjalankan —
  pengganti fitur variabel `-e KEY=VALUE` Maestro. Riwayat tetap di tabel
  `workflow_runs` yang sudah ada (kolom `flow_file` sekarang berisi path
  `.json`, bukan `.yaml` — tanpa migrasi rename kolom, demi kompatibilitas).

**Dihapus total:** `services/maestro.py`, seluruh isi lama `routes/workflow.py`
& `static/workflow.js` (ditulis ulang total), field Path Maestro CLI/Studio
di Pengaturan, folder `flows/` (diganti `scripts/`), langkah Java 17+ &
Maestro CLI di `setup-windows.bat` (8→6 langkah) & `setup-ubuntu.sh`
(7→5 langkah), setting `maestro_path`/`maestro_studio_path`/
`workflow_delay_min_ms`/`workflow_delay_max_ms` (dengan migrasi
`_migrate_remove_maestro_settings()` yang membersihkan DB lama user secara
otomatis & idempotent).

**UI baru (`templates/index.html` + `static/workflow.js`, ditulis ulang
total):** kartu "Rekam Aktivitas" (pilih HP → Mulai Rekam → tombol Rekam
Teks/Back/Home/Enter saat aktif → Stop & Tinjau), kartu "Tinjau & Edit
Langkah" (tabel step dg tombol naik/turun/edit-teks/hapus + edit jeda inline,
lalu Simpan Skrip), kartu "Skrip Tersimpan & Eksekusi" (kotak variabel teks
otomatis muncul kalau skrip punya `text_var`).

- [x] **Teruji (otomatis, pakai fake `adb`+`scrcpy` yang mensimulasikan
  getevent/wm size/uiautomator dump/input karena sandbox tak punya Android
  fisik):**
  - Deteksi device sentuh & resolusi layar, normalisasi koordinat mentah→pixel.
  - Alur rekam end-to-end: 1 tap + 1 swipe dari `getevent` tiruan terklasifikasi
    benar (tap vs swipe berdasar jarak, durasi tekan-lama).
  - Deteksi elemen via `uiautomator dump` tiruan berhasil terpasang ke step tap.
  - Langkah manual (teks & tombol khusus) tergabung benar dengan urutan waktu.
  - CRUD skrip lengkap (simpan/list/rename/hapus, tolak nama bentrok tanpa
    overwrite).
  - Eksekusi end-to-end via HTTP (record/start → add-text/add-key →
    record/stop → scripts/save → run → poll log) — LULUS dg log akurat,
    termasuk `text_var` terisi nilai custom saat eksekusi.
  - Ditemukan & diperbaiki SEBELUM rilis: (a) konflik nama setting delay lama
    (3000-8000ms era-Maestro) yang awalnya membuat replay 10+ detik/langkah —
    diganti key baru `step_delay_min_ms/max_ms` dg default kecil; (b) kode
    redundan penentuan `wait_after_ms` pada langkah manual, dibersihkan.
  - `setup-windows.bat`/`setup-ubuntu.sh`: kurung batch & sintaks bash
    diverifikasi ulang seimbang setelah penghapusan blok Java/Maestro; CRLF
    Windows tetap murni; 0 sisa referensi "maestro"/"java" (kecuali histori
    di PROGRES.md ini).
  - Boot penuh aplikasi (HTML+JS+routes baru) dari environment bersih.
- [x] **ZIP:** `remote-hp-v1.1.12.zip`

---

### v1.1.11 — Perbaikan dari Laporan User: Caption Lama, Perekam Kosong (Maestro 2.6), Bug Echo ✅ SELESAI

Tiga masalah dilaporkan dari screenshot + log user yang menjalankan aplikasi
dari folder LAMA (`remote-hp-v1.1.7`) dengan `remote_hp.db` lama, memakai
Maestro CLI **2.6.1** (tanpa Maestro Studio Desktop).

**1. Template caption masih yang lama (over-claim) + kadang "Gagal memuat"**

Akar masalah: seed caption hanya jalan saat tabel KOSONG (`COUNT(*)==0`).
DB user sudah berisi 3 caption lama sejak versi lampau, jadi 10 caption netral
yang baru tak pernah masuk.

- Ditambah `_migrate_old_caption_seeds()` di `database/db.py` (dipanggil di
  akhir `_migrate()` setelah koneksi ditutup). Ia mencocokkan ISI 3 seed lama
  secara PERSIS (disimpan di list `_OLD_SEED_CAPTIONS`), lalu MENGHAPUS hanya
  baris yang cocok itu. Setelah terhapus, bila tabel jadi kosong,
  `_seed_defaults()` mengisi 10 template netral yang baru.
- Aman untuk data user: caption yang dibuat/diedit user tidak akan cocok
  dengan 3 string lama itu, jadi tidak ikut terhapus. Bila user sudah punya
  caption sendiri (tabel tak jadi kosong), seed baru TIDAK dipaksa masuk.
- Soal "Gagal memuat template caption": itu muncul karena server (jendela CMD)
  sudah ditutup → semua panggilan API mati. Itu perilaku wajar, bukan bug.

**2. "Buka Perekam" membuka localhost:9999 yang KOSONG**

Akar masalah: Maestro CLI **2.6.0+ MENGHAPUS** Maestro Studio web (:9999).
Kode lama tetap menjalankan `maestro studio`; prosesnya "hidup" (lolos cek
3 detik) sehingga dilaporkan ok & frontend membuka :9999 → halaman kosong.

- `services/maestro.py`: ditambah `parse_cli_version()` &
  `web_studio_supported()` (True hanya bila < 2.6). `start_studio()` dirombak:
  bila Maestro Studio Desktop ada → pakai itu (seperti sebelumnya); kalau
  tidak & CLI < 2.6 → jalankan studio web seperti dulu; kalau CLI ≥ 2.6 →
  TIDAK membuka apa-apa, melainkan mengembalikan pesan jelas (studio web sudah
  dihapus; pakai Maestro Studio Desktop, atau `maestro record namafile.yaml`
  di terminal, atau tulis skrip manual) beserta field `record_cmd`.
- `studio_status()` kini melaporkan `web_studio_supported`,
  `recorder_available`, dan `cli_version`.
- `static/workflow.js`: status perekam menampilkan keadaan "Perekam visual
  belum tersedia" secara jujur untuk CLI 2.6+ tanpa Desktop; tombol "Buka
  Perekam" disembunyikan bila memang tak ada perekam visual yang bisa dipakai
  (biar user tak klik lalu dapat blank); bila server menolak, panduan +
  `maestro record` ditampilkan sebagai kotak info (bukan sekadar toast).

**3. Bug kosmetik `setup-windows.bat`: `'langsung' is not recognized`**

Satu baris `echo    OK - winget berhasil dipasang & langsung terdeteksi.`
memakai `&` telanjang, yang di cmd.exe berarti pemisah perintah → cmd mencoba
menjalankan `langsung` sebagai perintah. Diperbaiki dengan meng-escape jadi
`^&`. (winget-nya sendiri tetap berhasil terpasang; ini hanya pesan error
kosmetik.)

- [x] **Teruji (otomatis):**
  - Migrasi caption: DB dengan 3 seed lama → jadi 10 caption netral (semua
    lolos `flag_risky_caption`, ≤3 hashtag). DB dengan seed lama + caption
    user → seed lama terhapus, caption user TETAP ADA, seed baru tidak dipaksa.
  - `parse_cli_version`/`web_studio_supported` benar (2.6→False, 2.5→True,
    None→False). `start_studio` dg CLI 2.6.1 palsu → ok:False, TANPA url 9999,
    berisi panduan + `record_cmd`. CLI 2.5.0 palsu → tetap buka web studio.
  - Integrasi HTTP meniru lingkungan user (CLI 2.6.1, tanpa Desktop, DB lama):
    `/api/settings/captions`=10 netral; `/api/workflow/status` studio
    `recorder_available=False`; `/api/workflow/studio/start`=500 tanpa url +
    `record_cmd`.
  - `setup-windows.bat`: pemindaian memastikan 0 `&` telanjang tersisa di echo;
    CRLF tetap murni; kurung batch seimbang.
  - Regresi penuh: slot batas 8, workflow run + injeksi + DELAY_MS, caption
    CRUD + regen ≤3 hashtag, semua aset statik OK, `node --check` lolos.
- [x] **ZIP:** `remote-hp-v1.1.11.zip`

---

### v1.1.10 — Auto-install Winget Sendiri (setup-windows.bat) ✅ SELESAI

Dari log setup user: `winget` ternyata tidak tersedia di komputer itu sama
sekali, sehingga ADB, scrcpy, dan Java (yang semuanya mengandalkan winget)
tidak bisa dipasang otomatis. Sebelumnya script hanya bisa menyerah ke
instruksi manual kalau winget tidak ada. Sekarang ditambahkan langkah baru
**[1/8] — paling awal, sebelum Python** (karena instalasi Python otomatis pun
memakai winget) yang mencoba memasang winget itu sendiri, tanpa perlu user
membuka Microsoft Store manual:

1. **Coba daftar-ulang dulu (cepat, tanpa unduh):** banyak PC yang sebenarnya
   sudah punya paket "App Installer" ter-provisioning tapi belum ter-register
   untuk user saat ini (skenario umum di profil Windows tertentu). Dicoba
   lewat `Get-AppxPackage -AllUsers Microsoft.DesktopAppInstaller | ForEach
   { Add-AppxPackage -Register ... }`.
2. **Kalau masih belum ada, unduh & pasang dari link resmi Microsoft:**
   `https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx` (dependensi) lalu
   `https://aka.ms/getwinget` (msixbundle App Installer/winget itu sendiri) —
   keduanya link resmi yang didokumentasikan Microsoft untuk provisioning di
   luar Store, dipasang via `Add-AppxPackage` (instalasi per-user, TIDAK perlu
   run-as-Administrator).
3. Setelah dipasang, `%LOCALAPPDATA%\Microsoft\WindowsApps` (lokasi App
   Execution Alias `winget.exe`) ditambahkan ke PATH sesi berjalan — folder
   ini BIASANYA sudah ada di PATH bawaan Windows, jadi langkah-langkah
   berikutnya (Python/ADB/scrcpy/Java) yang juga memanggil `winget` bisa
   langsung memakainya di RUN YANG SAMA, tanpa perlu tutup-buka terminal.
4. Kalau tetap gagal (mis. sideloading dinonaktifkan kebijakan grup,
   arsitektur non-x64, atau tanpa internet): tetap ada pesan fallback yang
   jelas — install manual lewat Microsoft Store ("App Installer") atau unduh
   `.msixbundle` dari GitHub `microsoft/winget-cli/releases`.

**Implementasi:** hanya `setup-windows.bat` yang berubah (tidak ada kode
aplikasi yang disentuh). Semua string PowerShell dalam `-Command "..."`
sengaja HANYA memakai petik tunggal (dan penggabungan `+` alih-alih
interpolasi `"$(...)"`) supaya tidak pernah bentrok dengan petik ganda
pembungkus argumen di `cmd.exe` — pola yang sama seperti perintah PowerShell
lain yang sudah ada di script ini. Langkah lama digeser: Python/venv/deps
jadi [2/8][3/8][4/8], ADB/scrcpy/Java/Maestro tetap [5–8]/8.

**Catatan jujur soal keterbatasan:** metode ini best-effort — sideloading appx
via `Add-AppxPackage` umumnya berhasil di PC konsumen biasa (paket ini
ditandatangani Microsoft), tapi bisa gagal di mesin dengan kebijakan Group
Policy yang membatasi sideloading, edisi Windows N/LTSC tertentu tanpa
komponen Store, atau arsitektur ARM64 (link VCLibs yang dipakai adalah versi
x64) — pada semua kasus itu script akan gagal dengan rapi dan tetap
menampilkan instruksi manual, bukan macet/crash.

- [x] **Teruji (statis, tanpa mesin Windows nyata):**
  - Kurung batch SELURUH file diverifikasi seimbang (mengabaikan komentar
    `REM` & isi string PowerShell yang sudah pasti 1 argumen utuh).
  - Argumen `-Command "..."` untuk blok winget & blok Maestro dipastikan TIDAK
    mengandung petik ganda ataupun `%` liar di dalamnya (yang bisa memutus
    argumen/memicu ekspansi batch tak sengaja), dan kurung `()`/kurawal `{}`
    kode PowerShell di dalamnya seimbang.
  - CRLF file tetap murni (0 LF telanjang) setelah seluruh penyisipan &
    pemindahan blok.
  - Urutan langkah diverifikasi manual: winget → Python → venv → deps → ADB →
    scrcpy → Java → Maestro (winget SEBELUM Python, karena instalasi Python
    otomatis juga bergantung padanya).
  - Boot aplikasi Python tetap normal (perubahan ini murni file `.bat`, tidak
    menyentuh kode aplikasi).
- [x] **ZIP:** `remote-hp-v1.1.10.zip`

---

### v1.1.9 — Patch: Unduhan Maestro (Windows) Bersih & Dilewati Bila Java Belum Siap ✅ SELESAI

Ditemukan dari log setup asli user: unduhan Maestro CLI di `setup-windows.bat`
memakai `Invoke-WebRequest` tanpa menekan progress bar-nya. Di sebagian
`cmd.exe`, PowerShell 5.1 merender progress bar itu sebagai teks `Writing web
request` / `Writing request stream... (Number of bytes written: N)` yang
terlihat seperti error/kerusakan, dan render progress bar juga bisa membuat
unduhan jauh lebih lambat. Selain itu, script tetap mengunduh Maestro CLI
(~200MB) meski Java 17+ belum siap — padahal Maestro tidak akan bisa
dijalankan tanpa Java, jadi unduhannya sia-sia dulu di kondisi itu (perilaku
ini sudah benar di `setup-ubuntu.sh`, tapi belum konsisten di Windows).

**Perbaikan (`setup-windows.bat` saja — tidak ada perubahan kode aplikasi):**
- `Invoke-WebRequest` sekarang diberi `$ProgressPreference='SilentlyContinue'`
  + `-UseBasicParsing` → unduhan lebih cepat & output konsol bersih (tidak ada
  lagi teks "Writing web request/stream" yang membingungkan).
- Blok cek/unduh Maestro CLI kini dibungkus `if not "!JAVA_OK!"=="1" (...)
  else (...)` — dilewati dengan pesan jelas bila Java 17+ belum siap, persis
  seperti perilaku `setup-ubuntu.sh`. User cukup jalankan setup lagi setelah
  Java terpasang.

- [x] **Teruji:** keseimbangan tanda kurung batch pada blok langkah 7
  diverifikasi ulang (skrip verifikasi awal sempat false-positive karena
  komentar `REM 1)/2)` — komentar itu sekaligus dirapikan agar tidak memuat
  pola angka+kurung-tutup), CRLF file tetap murni (0 LF telanjang), boot
  aplikasi tetap normal, `setup-ubuntu.sh` tidak disentuh & tetap valid
  (`bash -n`).
- [x] **ZIP:** `remote-hp-v1.1.9.zip`

---

### v1.1.8 — Auto-install Maestro + Variabel Injeksi + Overhaul Caption ✅ SELESAI

Tiga perubahan sekaligus.

**1. Setup script auto-install Java 17+ & Maestro CLI**

Sebelumnya Maestro cuma "disebut opsional" di catatan akhir setup. Sekarang
kedua setup script memasangnya otomatis, mengikuti pola yang sama persis
dengan ADB & scrcpy:
- `setup-ubuntu.sh`: langkah dinaikkan jadi 7. Langkah **[6/7]** cek `java
  -version`; kalau < 17 / tak ada → `apt-get install -y openjdk-17-jdk`.
  Langkah **[7/7]** cek `command -v maestro`; kalau tak ada & Java siap →
  `curl -fsSL "https://get.maestro.mobile.dev" | bash`, lalu `export PATH`
  menyertakan `~/.maestro/bin` untuk sesi setup + pesan agar buka terminal
  baru bila PATH belum aktif.
- `setup-windows.bat`: langkah dinaikkan jadi 7 (CRLF dijaga). **[6/7]** cek
  `java -version` (parse major version, handle gaya `1.8`); kalau < 17 →
  `winget install -e --id EclipseAdoptium.Temurin.17.JDK`. **[7/7]** cek `where
  maestro`; kalau tak ada → coba `scoop install maestro`, kalau tidak →
  unduh rilis resmi `maestro.zip` dari GitHub (`releases/latest`), ekstrak ke
  `%LOCALAPPDATA%\Maestro`, deteksi folder `bin`, lalu tambahkan ke **PATH
  user** (via PowerShell `SetEnvironmentVariable(...,'User')`, bukan sistem/
  admin) + aktifkan untuk sesi jendela.
- Catatan akhir kedua script & `CARA-SETUP.md` diubah: tidak lagi bilang
  "install manual", melainkan konfirmasi bahwa sudah dipasang otomatis + saran
  buka ulang terminal bila PATH belum kebaca + arahan unduh **Maestro Studio
  Desktop** untuk perekam visual.
- `services/maestro.py` → `get_maestro_path()` dapat fallback baru:
  `_known_maestro_locations()` (mis. `~/.maestro/bin/maestro`,
  `%LOCALAPPDATA%\Maestro\maestro\bin\maestro.bat`, shim scoop) supaya Maestro
  terdeteksi tepat setelah dipasang meski PATH sesi lama belum refresh.

**2. Variabel injeksi (-e) untuk eksekusi Maestro**

- `services/maestro.py`: `start_run()` kini menerima `variables` (dict).
  Ditambah `normalize_env_vars()` (validasi key = identifier, value→string,
  buang newline & kosong) yang menyuntikkan tiap pasangan sebagai
  `-e KEY=VALUE` ke `maestro test`. Baris perintah di log memangkas nilai
  panjang (mis. CAPTION) via `_cmd_for_display()`, tapi yang dikirim ke proses
  tetap utuh.
- `random_delay_ms()` (baru): meng-generate **DELAY_MS** acak di sisi Python
  (bukan di YAML) dari rentang setting `workflow_delay_min_ms` /
  `workflow_delay_max_ms` (default **3000–8000 ms**), aman walau setting rusak/
  terbalik. `routes/workflow.py` → endpoint `/run` menyuntik DELAY_MS otomatis
  tiap klik Jalankan kecuali user mengisinya sendiri → tiap akun beda jeda.
- UI: kartu eksekusi punya panel **Variabel** (ACCOUNT_NAME, CAPTION, + area
  bebas `KEY=VALUE` per baris) yang semuanya opsional; catatan menjelaskan
  DELAY_MS otomatis. Pengaturan punya kartu **Jeda Acak Workflow (min/max ms)**.

**3. Overhaul caption generator**

- `services/caption.py`: `_shuffle_hashtags()` + `generate_caption()` kini
  **memaksa maksimal 3 hashtag** (`MAX_HASHTAGS`) — berlaku untuk SEMUA
  template (lama/baru, seed/input user), dipotong SETELAH diacak agar variatif,
  sekaligus normalisasi `#` & buang duplikat.
- `database/db.py`: 3 caption seed lama yang over-claim ("bagus banget",
  "wajib punya", "checkout", 7 hashtag `#racuntiktok` dst) **diganti total**
  menjadi **10 template** bergaya perilaku/psikologi konsumen yang umum
  (kebiasaan riset sebelum belanja, penasaran, bandingkan pilihan, refleksi
  keputusan belanja) TANPA menyebut/memuji produk, TANPA ajakan checkout, dan
  hanya ≤3 hashtag netral (`#fyp #relatable #tips`, dll).
- `flag_risky_caption(text)` (baru): daftar frasa berisiko dikelompokkan
  (over-claim / klaim hasil / ajakan checkout langsung). Dipanggil saat user
  **menyimpan** template (endpoint `POST`/`PUT /api/settings/captions`) &
  live saat mengetik — kalau terdeteksi, UI menampilkan **PERINGATAN** yang
  menyebut frasa & kategorinya, TAPI tidak memblokir (keputusan akhir di user).
- CRUD template caption (yang sebelumnya belum terpasang) kini lengkap:
  endpoint list/create/update/delete + `check`, plus UI kelola template di
  halaman Pengaturan.

- [x] **Teruji (otomatis):**
  - `normalize_env_vars` (skip key/nilai invalid, newline→spasi), `random_delay_ms`
    (rentang default/custom/terbalik/setting rusak), run end-to-end via maestro
    palsu → `-e ACCOUNT_NAME`, `-e CAPTION`, `-e DELAY_MS` tersuntik; nilai
    panjang terpangkas di tampilan tapi utuh di ARGS asli.
  - Seed caption: 10 template, semua LULUS `flag_risky_caption` (tak ada frasa
    berisiko) & ≤3 hashtag; `generate_caption` memotong template ber-7-hashtag
    jadi ≤3 dengan variasi.
  - Endpoint caption CRUD + check: risky terdeteksi (tetap tersimpan/201),
    netral lolos, kosong ditolak.
  - `get_maestro_path` fallback lokasi instalasi tidak crash.
  - Sintaks kedua setup script valid (bash -n) & `setup-windows.bat` tetap CRLF
    murni (0 LF telanjang).
  - Regresi: slot batas 8, boot penuh, semua elemen HTML baru ada, JS lolos
    `node --check`.
- [x] **ZIP:** `remote-hp-v1.1.8.zip`

---

### v1.1.7 — Slot Aplikasi (Original/Kloning) + Workflow Otomatisasi (Maestro) ✅ SELESAI

Dua fitur besar dalam satu versi.

**1. SLOT APLIKASI per HP (Original / Kloning)**

Fakta lapangan: dalam 1 HP Xiaomi/Redmi, TikTok bisa dipasang DUA KALI lewat
fitur bawaan **Aplikasi Ganda** (Dual Apps) — satu aplikasi **Original**, satu
aplikasi **Kloning**. Tiap aplikasi hanya sanggup menampung **maksimal 8 akun**,
jadi total **16 akun per HP**, terbagi 2 slot.

Struktur data lama (HP → langsung Akun) diganti mengikuti kenyataan itu:
> **HP → Slot Aplikasi (`app_slot`: 'original' | 'kloning') → Akun**

Soal penamaan: dipilih memakai **kata**, bukan angka ("Aplikasi 1/2"), sesuai
permintaan. Istilahnya **"Aplikasi Original"** dan **"Aplikasi Kloning"** —
karena itulah nama/istilah yang dipakai fitur Aplikasi Ganda Xiaomi sendiri,
jadi user langsung paham slot mana yang dimaksud tanpa perlu mengingat nomor.

Implementasi:
- `database/schema.sql` + `database/db.py`: kolom baru `accounts.app_slot`
  (default `'original'`). **Migrasi otomatis**: DB lama (v1.1.6) yang belum
  punya kolom ini akan ditambahi lewat `ALTER TABLE`, dan semua akun lama
  otomatis dianggap milik slot **Original** — tidak ada data yang hilang.
- `routes/accounts.py` (ditulis ulang): validasi slot, **batas keras 8 akun
  per slot** ditegakkan saat tambah akun DAN saat memindahkan akun antar-slot
  lewat edit. Endpoint baru `GET /api/accounts/slots` (info konstanta),
  filter `?app_slot=` pada list. Batas ditegakkan di API (bukan SQL) supaya
  data lama yang mungkin >8 tetap terbaca.
- `routes/devices.py`: list HP kini menyertakan `account_count_original` &
  `account_count_kloning`.
- `routes/history.py`: kolom `account_app_slot` diekspos + filter `?app_slot=`.
- `static/app.js`: sidebar akun sekarang **dikelompokkan per slot** dengan
  header ("📱 Aplikasi Original 3/8", "📲 Aplikasi Kloning 8/8"), tombol
  "+ Tambah Akun" per slot, dan slot penuh ditandai non-aktif. Modal akun
  punya dropdown pemilih slot. Info Akun, breadcrumb, dan tabel riwayat
  menampilkan badge slot.
- `static/style.css`: styling `.slot-group`, `.slot-head`, `.slot-badge`, dst.

**2. WORKFLOW OTOMATISASI (Maestro)**

Fondasi untuk "eksekusi workflow otomatis berdasarkan skrip". Setelah menimbang,
dipilih **Maestro** (https://docs.maestro.dev) sebagai mesinnya karena:
- Bekerja lewat **ADB** — infrastruktur yang SUDAH dipakai aplikasi ini.
- **Maestro Studio** menyediakan **perekam** (record) visual sesuai permintaan.
- Skrip berupa **file YAML** yang mudah dibaca & dimodifikasi manual — cocok
  persis dengan alur: **rekam → download → modifikasi → upload → simpan**.
- `maestro test <flow>.yaml --device <serial>` mengeksekusi skrip ke HP
  tertentu → siap untuk otomatisasi penuh ke depan.

Alur kerja yang didukung (persis permintaan):
1. **Rekam** — tombol "Buka Perekam" meluncurkan Maestro Studio (Desktop bila
   terdeteksi; fallback studio web CLI lama). Workspace diarahkan ke `flows/`.
2. **Download** — tiap skrip bisa diunduh (⬇️) untuk dimodifikasi.
3. **Upload + Simpan** — file yang sudah dimodifikasi di-upload lalu **Simpan**
   (tombol khusus). Ada juga editor in-app untuk menyunting langsung.
4. **Eksekusi** — pilih HP tujuan, klik "Jalankan" → `maestro test` berjalan di
   background dengan **log live** yang ter-stream ke konsol UI; hasil dicatat.

Implementasi:
- `services/maestro.py` (baru): deteksi Maestro CLI (`cli_status`, ramah pesan
  bila Java 17+ belum ada), peluncur perekam (`start_studio` — Desktop/CLI,
  auto-detect, deteksi CLI ≥2.6 yang sudah menghapus studio web), manajemen
  file skrip di folder `flows/` dengan **proteksi path-traversal** &
  sanitasi nama, dan **eksekutor** (`start_run`/`run_state`/`stop_run`) dengan
  thread pembaca log + watchdog timeout 30 menit.
- `routes/workflow.py` (baru): endpoint status, perekam start/stop, CRUD file
  skrip (list/content/download/save/upload/delete/rename), dan run
  start/status/stop + riwayat.
- `database/schema.sql`: tabel baru `workflow_runs` (riwayat eksekusi; file
  skrip sendiri disimpan sebagai file — filesystem = sumber kebenaran supaya
  hasil rekaman Maestro Studio langsung terbaca).
- `static/workflow.js` (baru) + halaman "Workflow" di `templates/index.html`:
  status bar, perekam, upload+simpan, editor, daftar skrip + eksekusi, konsol
  log live (polling), dan riwayat eksekusi.
- `database/db.py`: setting baru `maestro_path` & `maestro_studio_path`
  (kosong = auto-detect) — bisa diisi di **Pengaturan → Path Sistem**.
- Setup script (Ubuntu/Windows): catatan opsional cara memasang Maestro
  (butuh Java 17+); Maestro **tidak** diinstall otomatis karena berat, dan
  merekam/menyunting skrip tetap bisa tanpanya.

- [x] **Teruji (otomatis):**
  - Slot: batas 8 akun/slot (tambah & pindah slot), hitungan per slot akurat,
    list by slot, pindah slot gagal saat tujuan penuh & sukses saat ada tempat.
  - Migrasi DB v1.1.6 → v1.1.7: akun lama jadi 'original', tabel workflow_runs
    dibuat, tanpa kehilangan data.
  - Workflow: simpan/upload/download/rename/delete, sanitasi nama file
    (spasi→'-', paksa .yaml), tolak non-YAML, **path-traversal ditolak**,
    guard "HP tidak online / CLI belum siap / HP sibuk".
  - Eksekutor (maestro palsu): log live, transisi status success/failed,
    pencatatan riwayat.
  - Regresi: alur upload (scan + start session) tetap jalan; settings
    round-trip untuk path Maestro; filter history `?app_slot=`.
- [x] **ZIP:** `remote-hp-v1.1.7.zip`

---

### PATCH v1.1.5 — Fix Video Tidak Muncul di Galeri HP ✅ SELESAI
Memperbaiki masalah **video yang berhasil dipindahkan ke HP (terlihat di File
Manager) tapi tidak muncul di aplikasi Galeri**.

**Penyebab (`services/adb.py`):** `push_file()` sebelumnya hanya menjalankan
`adb push` — operasi filesystem murni. File benar-benar tersalin ke
`/sdcard/DCIM/RemoteHP/`, sehingga File Manager (baca filesystem langsung)
bisa melihatnya. Tapi aplikasi Galeri membaca daftar media dari **MediaStore**
(database index Android), bukan dari filesystem. `adb push` tidak memberi tahu
Android ada file baru, jadi MediaStore tidak ter-update dan Galeri tidak
menampilkan file sampai ada media scan (mis. HP di-restart).

**Solusi:** ditambahkan fungsi `scan_media(serial, remote_path)` yang mengirim
broadcast `android.intent.action.MEDIA_SCANNER_SCAN_FILE` via ADB shell.
Fungsi ini otomatis dipanggil di dalam `push_file()` tepat setelah push
berhasil, sehingga file langsung ter-index MediaStore dan muncul di Galeri
tanpa perlu restart HP. Status hasil scan (`media_scan_ok`) ikut dikembalikan
dan ditampilkan di console log UI (`routes/upload.py`) — kalau scan gagal
(mis. dibatasi vendor tertentu), user tetap diberi tahu lewat warning, file
tetap aman terkirim.

**Catatan:** kalau di HP tertentu (custom ROM/vendor skin galeri) masih belum
muncul juga, opsi lanjutan yang belum diimplementasikan: trigger scan seluruh
storage via `ACTION_MEDIA_MOUNTED`, atau insert langsung ke
`content://media/external/file` via `adb shell content insert`.

---

### PATCH v1.1.5 — Tuning Realtime Mirror (USB + HP Kelas Bawah) ✅ SELESAI
Mempercepat mirror layar HP (scrcpy) mendekati real-time, khusus untuk
skenario: **selalu pakai kabel USB** + **HP kelas menengah-bawah** (mis.
Redmi 9T dan sekelasnya — chipset MediaTek Helio G-series / Snapdragon 4xx).

**Penyebab lag (`services/scrcpy.py`):** sebelumnya `launch()` meluncurkan
scrcpy tanpa satupun flag performa — resolusi native (1080p+), bitrate tak
terbatas, fps tak terbatas, dan audio ikut di-stream. Di chipset budget,
hardware H.264 encoder-nya ADA tapi gampang keteteran kalau dipaksa encode
sebesar itu sekaligus; begitu encoder keteteran ia mulai antre/drop frame —
itulah yang terasa sebagai lag, walaupun koneksinya sudah kabel USB (jadi
bukan masalah bandwidth/koneksi, tapi beban encode di sisi HP).

**Solusi:** ditambahkan `PERFORMANCE_ARGS` yang otomatis dipakai di setiap
`launch()`:
- `--video-codec=h264` — paling ringan & pasti hardware-accelerated di
  chipset budget (hindari h265/av1 yang di sebagian chipset murah jatuh ke
  software encode yang jauh lebih lambat)
- `--max-size=720` — turunkan sisi terpanjang video jadi 720px, beban encode
  turun drastis dibanding native 1080p+
- `--video-bit-rate=2M` — bitrate rendah → buffer kecil → delay kecil
- `--max-fps=30` — cukup untuk kerja/monitoring, jauh lebih ringan drpd 60fps
- `--no-audio` — skip 1 pipeline decode audio penuh
- `--video-buffer=0` — matikan buffer smoothing di sisi PC, tampilkan frame
  secepat diterima

Hasil: delay mirror ditargetkan turun ke kisaran <100ms via USB (mendekati
real-time), dengan trade-off resolusi & bitrate lebih rendah (masih cukup
jernih untuk kerja/monitoring, bukan untuk menonton konten HD).

**Catatan:** kalau nanti device yang dipakai lebih flagship / butuh kualitas
visual lebih tinggi, angka `--max-size`/`--video-bit-rate`/`--max-fps` di
`PERFORMANCE_ARGS` bisa dinaikkan lagi manual di kode.

---

### v1.1.5 — Upload Nama Sama Bebas + Audit Windows ✅ SELESAI
Memperbaiki aturan anti-duplikasi agar sesuai alur kerja nyata, dan memastikan
aplikasi berjalan normal di Windows.

**1. Anti-duplikasi: riwayat jadi CATATAN, bukan penghalang (`services/guard.py`)**
Masalah v1.1.4: identitas video = (nama file + tanggal batch). Akibatnya, nama
file yang sama TIDAK bisa diupload dua kali di hari yang sama — padahal user
memang sering menghasilkan batch berbeda (isi beda) dengan penomoran nama yang
sama (`video_0001.mp4`, dst.) di hari yang sama.

Kenyataan: setiap video yang sukses diupload LANGSUNG DIHAPUS dari PC & HP
(lihat langkah `confirm` & `finish` di `routes/upload.py`). Jadi proteksi
anti-duplikasi yang sebenarnya adalah **file fisiknya hilang** — scan berikutnya
tidak akan menemukannya lagi. Mencocokkan "nama yang pernah diupload" justru
salah karena memblokir konten baru yang sah.

Kebijakan baru:
- Nama file sama + **hari sama** + isi beda → **BOLEH** diupload.
- Nama file sama + akun sama → **BOLEH** (guard tidak lagi memblokir).
- Tabel `uploaded_videos` tetap mencatat semua upload untuk **riwayat/catatan**
  (tanggal berapa upload apa) — tidak lagi dipakai sebagai gerbang.
- Proteksi dobel-upload yang tak disengaja tetap ada lewat: (a) penghapusan
  file otomatis setelah upload, dan (b) alur FIFO per sesi (tiap video ditandai
  'done', tidak bisa dikirim dua kali dalam satu sesi).
- `guard.is_uploaded()` / `filter_uploadable()` / `can_upload()` dipertahankan
  signature-nya (tidak pernah menandai duplikat lagi) agar kode pemanggil aman.
- `static/upload.js`: label hasil scan disederhanakan (tidak menampilkan
  "0 duplikat").

**2. Audit kompatibilitas Windows (tanpa perubahan kode diperlukan)**
Diperiksa menyeluruh; aplikasi sudah cross-platform dengan benar:
- `services/adb.py` & `services/scrcpy.py`: memilih `adb.exe`/`scrcpy.exe` di
  Windows via `platform.system()`; `scrcpy._spawn_detached()` memakai
  `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` di Windows dan `start_new_session`
  di POSIX; fokus jendela punya jalur PowerShell khusus Windows.
- Semua operasi path lokal memakai `os.path.*` (= `ntpath` di Windows):
  `join`, `basename`, `dirname`, `splitext`, `expanduser("~")`. Tidak ada path
  Unix yang di-hardcode, tidak ada `shell=True`, tidak ada `os.system`.
- Path folder target di HP (`/sdcard/...`) memang selalu forward-slash di kedua
  OS (itu path Android, benar).
- `setup-windows.bat` & `jalankan-windows.bat`: line ending CRLF (benar untuk
  cmd.exe), auto-install Python/ADB/scrcpy via winget, perbaikan `.venv` rusak.
- DB (`database/db.py`): path via `os.path.abspath`/`join`; `host=0.0.0.0` OK.

- [x] **Teruji (otomatis):**
  - Skenario nama sama + hari sama + akun sama → BOLEH upload (bukan duplikat)
  - Alur penuh 2 batch beda dengan nama file sama di hari sama → keduanya
    terupload & tercatat di riwayat (6 video, tiap nama muncul 2x)
  - Statistik hari ini tetap akurat
  - Boot aplikasi + endpoint (scan tanpa tanggal ditolak, folder salah → 404)
  - Simulasi path Windows (ntpath): join/basename/splitext/dirname benar
- [x] **ZIP:** `remote-hp-v1.1.5.zip`

---

### v1.1.4 — Panel Tanggal + Anti-Duplikasi Berbasis Tanggal Batch ✅ SELESAI
Menambahkan **variabel tanggal** ke alur upload, sekaligus memperbaiki masalah
anti-duplikasi yang mengganggu: video dari Video Mixer memakai
penomoran berulang tiap hari (`video_0001.mp4`, `video_0002.mp4`, …), sehingga
video baru hari ini tertahan karena namanya sama dengan yang kemarin.

**Masalah yang dipecahkan**
Anti-duplikasi lama mengunci pada `filepath`. Karena file dihapus setelah upload
lalu digenerate ulang besok dengan **nama & path yang sama**, kunci ini salah:
path yang sama pasti muncul lagi keesokan harinya. Akibatnya video hari ini
dikira duplikat dari video kemarin.

**Solusi: tanggal sebagai variabel baru + kunci duplikasi baru**
Identitas video kini = **(nama file + tanggal batch)**. Nama file sama BOLEH
diupload lagi selama **tanggal batch berbeda** (opsi yang dipilih). Duplikat
sejati (nama sama + tanggal sama) tetap tertahan.

**1. Panel 1 — Tanggal Jadwal & Batch (`static/upload.js`, `static/style.css`)**
- Panel baru menjadi **Panel 1**; "Pilih Folder Video" bergeser jadi **Panel 2**.
- **Kalender bulanan** buatan sendiri (tanpa dependensi): jumlah hari benar
  per bulan (28/29/30/31, termasuk kabisat), navigasi bulan prev/next dengan
  wrap-around tahun, highlight **hari ini** (outline biru) & **tanggal terpilih**
  (isi biru).
- Tombol **📅 Hari Ini** untuk memilih tanggal hari ini seketika.
- Kotak "Tanggal Terpilih" menampilkan format panjang (mis. "Selasa, 30 Juni 2026")
  + ISO (`2026-06-30`).
- Scan folder **wajib** memilih tanggal dulu (tervalidasi di frontend & backend).
- Tanggal jadwal ditampilkan juga di **Panel 4 (Jadwal Post)** sebagai penanda
  agar semua post di-set ke tanggal tsb di TikTok Studio.
- Sesuai kebutuhan: **tidak ada pemilihan jam** di panel ini — jam tetap
  dihasilkan generator jadwal (Time Randomizer) yang sudah ada.

**2. Anti-duplikasi berbasis tanggal (`services/guard.py`)**
- `is_uploaded(filename, batch_date)` & `filter_uploadable(videos, batch_date)`
  kini mencocokkan **(filename + batch_date)**, bukan `filepath`.
- Nama file sama + tanggal beda → **boleh** diupload; nama sama + tanggal sama
  → **duplikat**.

**3. Scope subfolder "sudah diproses" per tanggal (`routes/upload.py`)**
- `_processed_subfolders(...)` kini di-scope per `batch_date`. Tanpa ini,
  subfolder `1/` akan terkunci selamanya setelah dipakai sekali (karena nama
  subfolder juga berulang tiap hari). Kini subfolder "reset" untuk tanggal baru.
- Endpoint `scan` & `start` menerima, memvalidasi, dan meneruskan `batch_date`;
  `confirm` menyimpannya ke `uploaded_videos` (sumber: baris sesi, bukan klien).

**4. Database (`database/schema.sql`, `database/db.py`)**
- Kolom baru `batch_date` di `upload_sessions` & `uploaded_videos`.
- Index baru `idx_videos_name_date (filename, batch_date)` untuk cek duplikat cepat.
- **Migrasi otomatis & aman** untuk DB lama v1.1.3: `ALTER TABLE ADD COLUMN`
  dijalankan **sebelum** schema.sql (agar index kolom baru tidak gagal),
  idempotent, dan data lama tetap utuh (`batch_date` = NULL).

**5. Validasi tanggal (`services/scheduler.py`)**
- `valid_batch_date()` menolak tanggal kalender tidak sah (mis. `2026-02-30`),
  hanya menyimpan `YYYY-MM-DD` yang valid.

**6. History lebih informatif (`static/app.js`, `templates/index.html`)**
- Kolom **"Tanggal Batch"** di tabel Riwayat + field tanggal di modal detail,
  supaya mudah melihat tanggal berapa sudah upload berapa video.

- [x] **Teruji (otomatis):**
  - Migrasi DB v1.1.3 → v1.1.4 aman & idempotent, data lama terjaga
  - Guard: nama sama + tanggal beda = boleh; nama sama + tanggal sama = duplikat
  - Alur penuh 2 hari (scan→start→push→confirm→finish): file dengan nama sama
    bisa diupload lagi di tanggal berikutnya, tertahan bila tanggal sama
  - Subfolder ter-scope per tanggal (tidak terkunci selamanya)
  - Validasi tanggal (tolak 2026-02-30, dsb.)
  - Kalender: jumlah hari benar (28/29/30/31 + kabisat + tahun abad),
    navigasi wrap-around, format ISO tanpa geser timezone
  - Boot aplikasi dengan DB baru + endpoint menolak scan/start tanpa tanggal
- [x] **ZIP:** `remote-hp-v1.1.4.zip`

---

### v1.1.3 — Policy 4/5/24/Manual + Jadwal Post Adaptif ✅ SELESAI
Menyamakan opsi dengan Video Mixer dan membuat jadwal posting
mengikuti banyaknya video per folder.

**1. Policy folder (panel "Pilih Folder Video")**
Sebelumnya hanya: `4`, `5`, `All/Manual`. Sekarang: `4`, `5`, `24`, `All`,
dan `Manual` (muncul kolom angka untuk isi sendiri, mis. 10). Nilai policy
ikut tercatat di sesi seperti sebelumnya.

**2. Jadwal Post (TikTok Studio) — panel 4**
Jam dasar kini otomatis menyesuaikan **jumlah video** dalam folder (1 video =
1 post), terhubung dengan **Jadwal Default** di Pengaturan:
- Jumlah ≤ daftar Jadwal Default (mis. 4) → ambil jam pertamanya:
  - 4 → `09:00, 12:00, 15:00, 18:00`
  - 5 → `09:00, 12:00, 15:00, 18:00, 21:00`
- Jumlah melebihi daftar default → **sebar merata 24 jam**:
  - 24 → `00:00, 01:00, 02:00, … 23:00` (tiap jam)
  - mis. 10 → tersebar rata sepanjang hari
- **Rentang Acak Default (menit)** tetap berlaku di semua kasus — tiap jam
  dasar digeser maju acak 0..rentang (tidak pernah lebih awal).

- [x] `services/scheduler.py`: helper `_even_spread()` + `_base_hours()`;
  `generate_schedule()` tidak lagi memutar (cycle) jam saat jumlah > default,
  melainkan menyebar merata 24 jam (jumlah 24 → tepat tiap jam)
- [x] `static/upload.js`: tombol policy `4 / 5 / 24 / All / Manual` + kolom
  input manual (state `Upload.isManual`), nilai dikirim ke scan & start
- [x] **Teruji:** count 4/5/24/10 menghasilkan jam dasar sesuai spesifikasi,
  rentang acak 15 menit tetap diterapkan (offset 0..15), alur `start_session`
  & `regen-schedule` lewat DB asli lolos
- [x] **ZIP:** `remote-hp-v1.1.3.zip`

---

### v1.1.2 — Mode Mirror: Anti-Sleep & Hemat Daya ✅ SELESAI
Dua kendala pemakaian jendela mirror scrcpy:
1. **HP sleep saat idle** → begitu tidak ada interaksi, HP tidur dan jendela
   mirror berhenti merespons mouse & keyboard.
2. **Boros listrik** → selama mirror, layar fisik HP ikut menyala terus.

**Solusi:** opsi mode mirror baru di **Pengaturan → Path Sistem**, yang
menyisipkan flag scrcpy saat tombol 🖥️ Mirror ditekan. Ada 2 pilihan:
- **Anti-sleep (default)** → `--stay-awake`
  HP tidak akan tidur selama jendela mirror terbuka, jadi mouse & keyboard
  tetap responsif tanpa harus menyentuh HP.
- **Anti-sleep + Matikan layar HP** → `--stay-awake --turn-screen-off`
  Sama seperti di atas, plus layar fisik HP dimatikan agar hemat listrik.
  Mirror di komputer tetap berjalan normal.

- [x] `services/scrcpy.py`: konstanta `SCRCPY_MODES` + `SCRCPY_MODE_DEFAULT`,
  helper `get_scrcpy_mode()` (fallback aman jika nilai kosong/ngaco) &
  `mode_args()`; `launch()` menambahkan `mode_args()` ke command scrcpy
- [x] `database/db.py`: seed default `scrcpy_mode = "stay_awake"` (DB lama
  otomatis dianggap default lewat fallback — tidak perlu migrasi manual)
- [x] `routes/settings.py`: validasi `scrcpy_mode` hanya menerima 2 nilai sah,
  selain itu dipaksa ke `stay_awake`
- [x] `templates/index.html`: dropdown **Mode Mirror Layar (scrcpy)** dengan
  penjelasan singkat tiap pilihan
- [x] `static/app.js`: `loadSettings()` & tombol Simpan memuat/menyimpan
  `scrcpy_mode`
- [x] **Teruji:** DB lama tanpa setting → command pakai `--stay-awake`;
  pilihan 1 → `--stay-awake`; pilihan 2 → `--stay-awake --turn-screen-off`;
  nilai ngaco di DB/POST → fallback aman; seed default & validasi lulus
- [x] **ZIP:** `remote-hp-v1.1.2.zip`

---

### v1.11 — Anti Jendela Mirror Dobel ✅ SELESAI
Laporan pengguna: klik 🖥️ pada HP yang sama 3x → muncul 3 jendela scrcpy.

**Solusi:** aplikasi mengingat proses scrcpy yang sedang hidup per serial.
- [x] `services/scrcpy.py`: registry `_PROCS` (per serial) + lock thread-safe
  - `launch()` cek `proc.poll()`: jika jendela serial itu masih hidup →
    TIDAK buka baru, coba fokuskan jendela lama (best-effort), kembalikan
    `already_open: True`
  - Jika jendela sudah ditutup → buka baru lagi (registry dibersihkan)
  - `_try_focus_window()` cross-platform: Linux pakai wmctrl/xdotool,
    Windows pakai PowerShell+WinAPI (SetForegroundWindow). Gagal fokus
    TIDAK fatal — jendela tetap ada.
  - `close()` & `active_serials()` untuk kelengkapan
  - Judul jendela unik "RemoteHP-Mirror: <nama>" agar bisa dicari WM
- [x] `routes/devices.py`: endpoint mirror meneruskan `already_open`/`focused`
- [x] `static/app.js`: toast beda — "Jendela mirror dibuka" (baru) vs
  "Jendela mirror HP ini sudah terbuka" (sudah ada)
- [x] `app.py`: `debug=False` + `use_reloader=False` — 1 proses stabil supaya
  registry jendela konsisten, sekaligus hapus debugger Werkzeug yang sensitif
- [x] `setup-ubuntu.sh`: install `wmctrl` (opsional, untuk fokus jendela);
  anti-dobel tetap jalan tanpanya
- [x] **1 jendela per HP** (ganti device tetap punya jendelanya sendiri — masuk akal)

**Cross-platform (Windows & Ubuntu dua-duanya lancar):**
- Anti-dobel inti pakai `Popen.poll()` → identik di semua OS, tidak butuh tool
  tambahan
- Fokus jendela: wmctrl/xdotool (Linux) vs PowerShell (Windows, selalu ada)

- [x] **Teruji:** klik sama 3x → 1 proses scrcpy dibuka (call 2&3 already_open=True,
  focused=True); device beda → jendela sendiri; tutup → klik lagi buka fresh;
  app boot 200 OK (debug off); JS/HTML/Python/bash valid
- [x] **ZIP:** `remote-hp-v1.11.zip`

---

### v1.10 — Mirror Layar HP (scrcpy) ✅ SELESAI
Permintaan pengguna: integrasikan mirroring scrcpy ke aplikasi supaya tidak
perlu buka scrcpy manual / bolak-balik, bisa ganti device yang di-mirror.

**Catatan teknis penting:** scrcpy adalah app desktop, web app TIDAK bisa
menanam jendelanya ke dalam browser (batasan browser). Solusi: aplikasi
MELUNCURKAN scrcpy untuk serial HP tertentu → jendela scrcpy muncul terpisah,
tapi user cukup klik 1 tombol (tak perlu terminal). Ini menyederhanakan
workflow sesuai tujuan.

- [x] `services/scrcpy.py` (BARU) — pola sama seperti adb.py:
  - `get_scrcpy_path()` cross-platform (override via settings 'scrcpy_path')
  - `is_available()` cek scrcpy terinstall + versi
  - `launch(serial, title)` luncurkan NON-BLOCKING (detached): jendela hidup
    sendiri, request HTTP langsung kembali. Aman di Windows & POSIX.
- [x] `routes/devices.py`:
  - `GET /api/devices/scrcpy-status` — cek scrcpy terinstall (untuk UI)
  - `POST /api/devices/<id>/mirror` — luncurkan mirror; validasi serial ada &
    HP online dulu, pesan error jelas Bahasa Indonesia
- [x] `database/db.py`: tambah setting default `scrcpy_path` (kosong = auto)
- [x] `static/app.js`: tombol 🖥️ Mirror di tiap kartu HP (stopPropagation biar
  tak bentrok dgn dblclick edit), handler `mirrorDevice()` + toast
- [x] `static/style.css`: style tombol mirror + container `.hp-card-actions`
- [x] `templates/index.html`: field "Path scrcpy" di Pengaturan + hint
- [x] `static/app.js`: load & save `scrcpy_path` di Pengaturan
- [x] `setup-ubuntu.sh`: langkah [5/5] auto-install scrcpy via apt (+ instruksi
  distro lain: dnf/pacman/snap)
- [x] `setup-windows.bat`: langkah [5/5] auto-install scrcpy via winget
  (Genymobile.scrcpy) + instruksi manual; line ending CRLF dijaga
- [x] `CARA-SETUP.md`: bagian "Mirror layar HP (scrcpy)"

**Beda Windows vs Ubuntu (di balik layar saja, bagi user SAMA — klik tombol):**
- Path default: `scrcpy.exe` (Windows) vs `scrcpy` (Linux)
- Spawn detached: creationflags DETACHED_PROCESS (Windows) vs
  start_new_session (POSIX)
- Auto-install: winget (Windows) vs apt (Ubuntu)

- [x] **Teruji:** app boot 200 OK; scrcpy-status & mirror endpoint balas dengan
  pesan jelas saat scrcpy/HP belum siap; 2 tombol Mirror ter-render di sidebar;
  field path scrcpy muncul di Pengaturan; JS/HTML/Python/bash valid
- [x] **ZIP:** `remote-hp-v1.10.zip`

---

### v1.09 — Hapus Jadwal Generator + Penanda Warna Jam ✅ SELESAI
Dua permintaan pengguna:

**1. Hapus "Jadwal Generator" yang berdiri sendiri.**
- Alasan: di dalam workflow upload (panel no.4 "Jadwal Post (TikTok Studio)")
  sudah ada jadwal otomatis, jadi generator terpisah jadi redundan.
- [x] Blok Jadwal Generator + Hasil Jadwal dihapus dari halaman Upload (HTML)
- [x] Fungsi terkait dihapus dari `app.js` (Jadwal object, initJadwalPage,
      generateJadwal, saveJadwalDefault, renderJadwalResult, dll.)
- [x] Halaman Upload kini bersih: hanya area kerja upload + statistik + riwayat
- [x] Endpoint backend jadwal tetap (dipakai workflow), tidak ada ID dobel

**2. Kolom jam (Post 1–5) di panel no.4 berubah warna sesuai status.**
- Tujuan: penanda visual urutan upload + cegah jam posting dobel.
- [x] `static/upload.js`: tiap kolom jadwal mengikuti status video di indeks
      yang sama —
        • selesai upload  → HIJAU + "✓ Selesai" + garis aksen hijau
        • sedang upload   → BIRU + "● Berlangsung" + garis aksen biru
        • belum           → abu + "Menunggu"
- [x] `static/style.css`: tambah state `.schedule-item.done` (hijau) &
      `.schedule-item.current` (biru), garis aksen kiri, badge `.schedule-status`
- [x] **Teruji (screenshot Chromium):** sesi 4 video dengan video-1 selesai →
      Post 1 hijau "✓ Selesai", Post 2 biru "● Berlangsung", Post 3–4 abu
      "Menunggu". Berubah otomatis seiring tiap video dikonfirmasi selesai.

- [x] **Teruji:** app boot 200 OK, JS/HTML/Python valid, menu tinggal 3
      (Upload/History/Pengaturan), halaman Upload kosong bersih tanpa sisa.
- [x] **ZIP:** `remote-hp-v1.09.zip`

---

### v1.08 — Fix Jadwal + Merge ke Upload + Folder Video ✅ SELESAI
Tiga permintaan pengguna:

**1. Bug jadwal mendasar — jadwal tidak boleh lebih awal dari jam dasar.**
- Dulu: `random.randint(-range, +range)` → bisa mundur (15:00 jadi 14:57). ❌
- Sekarang: `random.randint(0, +range)` → hanya MAJU. Misal 15:00 rentang 15
  → hasil 15:00–15:15. ✅
- [x] `services/scheduler.py` diperbaiki + docstring diperbarui
- [x] **Teruji:** 2000x generate, 0 pelanggaran; range 0 = tepat jam dasar;
      hasil nyata di UI: Post 3 base 15:00 → 15:15 (bukan 14:57 lagi)

**2. Jadwal Generator menyatu ke menu Upload (bukan menu terpisah).**
- Alasan: hindari bolak-balik menu.
- [x] Blok Jadwal Generator + Hasil Jadwal dipindah ke kolom kiri halaman Upload
- [x] Nav "Jadwal Generator" dihapus → menu tinggal: Upload, History, Pengaturan
- [x] `app.js`: `initJadwalPage()` dipanggil sekali saat startup (bukan saat
      pindah halaman); tidak ada ID dobel
- [x] `static/style.css` & routing tetap; halaman jadwal standalone dihapus

**3. Folder video bawaan + Path Storage default.**
- [x] Folder `video/` dibuat di dalam aplikasi + panduan `CARA-PAKAI-FOLDER-INI.txt`
- [x] `database/db.py`: default `storage_path` otomatis = path absolut folder
      `video/` (dihitung dari BASE_DIR, jadi benar di komputer manapun)
- [x] Auto-heal: DB lama dengan storage_path kosong otomatis diarahkan ke video/
- [x] `upload.js`: field path folder otomatis terisi storage path default
- [x] Pengguna cukup pindahkan subfolder (1, 2, 3, …) berisi video ke `video/`

**Bonus — Settings difungsikan:**
- [x] `app.js`: `loadSettings()` mengisi form dari DB + simpan via POST
- [x] Tombol "Simpan Pengaturan" & "Backup Database" aktif
- [x] `routes/settings.py`: endpoint `/api/settings/backup-db` (unduh file .db)
- [x] `.gitignore`: abaikan video user, simpan folder + panduan

- [x] **Teruji:** app boot 200 OK, semua endpoint OK, JS/HTML valid,
      screenshot Chromium (Upload+jadwal menyatu, jadwal maju-saja, Settings terisi)
- [x] **ZIP:** `remote-hp-v1.08.zip`

---

### v1.07 — Rombak Total UI/UX ✅ SELESAI
Dari laporan pengguna: semua halaman (Upload/History/Jadwal/Pengaturan)
tampil bertumpuk jadi satu di halaman depan — sidebar ada tapi panel utama
berantakan ter-split.

**Akar masalah:** CSS lama punya konflik — `.content { display:flex }`
menimpa `.page { display:none }`, sehingga halaman non-aktif tidak pernah
benar-benar disembunyikan dan semuanya menumpuk vertikal.

**Perbaikan + rombak (frontend saja; backend & semua logika tetap utuh):**
- [x] `static/style.css` ditulis ulang total (~700 baris):
  - **Routing benar**: `.page { display:none !important }` +
    `.page.active { display:block !important }`; Upload jadi grid 2 kolom
    saat aktif. Satu halaman tampil pada satu waktu (bug hilang).
  - Sistem desain konsisten: token warna/spacing/radius, app-shell modern,
    kartu, tombol (primary/ghost/success/danger), form, tabel, tag, modal,
    toast, empty-state, progress bar, ADB console.
  - Sidebar dipoles: logo pulse, nav indicator, kartu HP + akun nested rapi.
  - Animasi halus (page transition, hover, modal) + `prefers-reduced-motion`.
  - **Responsif**: Upload turun ke 1 kolom di layar < 1100px.
- [x] `templates/index.html` ditulis ulang:
  - Tiap halaman dibungkus `.page` + `.page-wrap` + `.page-head` yang rapi.
  - Upload = `.panel-left` (area kerja) + `.panel-right` (statistik & riwayat).
  - Semua 44 ID & hook yang dipakai app.js/upload.js dipertahankan persis.
- [x] `static/app.js`: Info Akun dipoles ke layout `.info-row` (key–value rapi).
- [x] `static/upload.js`: empty-state dibungkus kartu agar konsisten.
- [x] Perbaikan detail: header kartu HP tidak lagi tumpang-tindih dengan badge
      "X akun" (truncate + flex-shrink benar).
- [x] **Teruji visual (screenshot Chromium)**: ke-4 halaman tampil terpisah
      & rapi, workflow upload + Info Akun ter-render benar, sidebar rapi,
      layout responsif di 980px. App boot 200 OK, JS & HTML valid.
- [x] **ZIP:** `remote-hp-v1.07.zip`

---

### v1.06 — Fix venv tanpa pip + rapikan panduan ✅ SELESAI
Perbaikan dari laporan nyata pengguna di Ubuntu 24 (Python 3.12):
`No module named pip` saat langkah install dependency.

**Akar masalah:** ada folder `.venv` lama yang dibuat sebelum `python3-venv`
lengkap, jadi venv tsehat-nya cacat (tanpa pip). Script v1.05 melihat `.venv`
"sudah ada" lalu melewatinya — padahal rusak.

- [x] `setup-ubuntu.sh` diperbaiki:
  - Cek modul `ensurepip` (bukan cuma `venv`) saat deteksi Python → pasang
    `python3-pip` lewat apt bila kurang
  - **Validasi kesehatan `.venv`**: cek `.venv` benar punya pip; kalau tidak,
    `.venv` lama dihapus & dibuat ulang otomatis
  - Jaring pengaman `ensurepip --upgrade` bila pip masih hilang
  - Verifikasi final: pip wajib ada sebelum lanjut, dengan pesan perbaikan jelas
- [x] `setup-windows.bat` diberi perbaikan setara (validasi pip di `.venv`,
      rebuild bila rusak, fallback ensurepip)
- [x] `CARA-SETUP.md` dirapikan:
  - Semua perintah terminal jadi **satu baris flush-left**, siap copy-paste
    (sebelumnya ter-indent di dalam list → ikut ter-copy spasinya)
  - Tambah bagian troubleshooting khusus "No module named pip"
- [x] README: perintah Ubuntu jadi satu baris copy-paste
- [x] **Teruji:** reproduksi `.venv` rusak (tanpa pip) → script deteksi →
      rebuild → pip 24.0 muncul. Langkah 1 & 2 lolos bersih. App boot 200 OK.
- [x] **ZIP:** `remote-hp-v1.06.zip`

---

### v1.05 — Setup Turnkey 1-Klik ✅ SELESAI
Fokus: aplikasi **benar-benar siap pakai di komputer baru** (Ubuntu/Windows),
tanpa perlu paham teknis. Berjalan native di OS (bukan Docker), jadi disertakan
script setup otomatis.

- [x] `setup-windows.bat` — setup 1x untuk Windows:
  - Deteksi Python; auto-install via winget jika belum ada (lewati Store-stub palsu)
  - Buat virtual environment `.venv` terisolasi
  - Install dependency dari `requirements.txt`
  - Cek/auto-install ADB (Google.PlatformTools via winget) + instruksi manual
  - Pesan jelas Bahasa Indonesia + penanganan error tiap langkah
- [x] `jalankan-windows.bat` — run harian; buka browser otomatis ke :5001;
      cek dulu apakah sudah di-setup
- [x] `setup-ubuntu.sh` — setup 1x untuk Ubuntu/Linux:
  - Deteksi Python3 + modul venv; auto-install via apt (python3-venv, pip)
  - Buat `.venv`, install dependency
  - Cek/auto-install ADB (android-tools-adb) + instruksi distro lain
  - Output berwarna, deteksi sudo, fallback non-apt
- [x] `jalankan-ubuntu.sh` — run harian; buka browser otomatis; cek setup
- [x] `CARA-SETUP.md` — panduan pemula langkah-demi-langkah (Windows + Ubuntu +
      siapkan HP/USB Debugging + troubleshooting)
- [x] `.gitignore` — kecualikan `.venv/`, `remote_hp.db`, `__pycache__`
- [x] `requirements.txt` → `Flask>=3.0,<4.0` (lebih tahan di Python/komputer baru)
- [x] README diperbarui: bagian "Cara Menjalankan CEPAT" (script) + manual
- [x] **Teruji:** app boot + endpoint (/ , /api/devices, /api/settings,
      /api/history) semua 200 OK di port 5001
- [x] **ZIP:** `remote-hp-v1.05.zip`

**Yang sudah bisa dipakai di v1.05:**
- Tinggal salin folder ke komputer baru → klik/jalankan 1 file setup → pakai.
- Pindah komputer: salin folder (+ `remote_hp.db` jika mau bawa data).

---

### v1.00–v1.03 ✅ (ringkas)
Fondasi · Services · Upload Workflow FIFO (10 aturan ketat AKTIF) · Jadwal Generator

### v1.04 — History ✅ SELESAI
- [x] `routes/history.py` — **teruji:**
  - GET /api/history — list sesi + filter (device_id, account_id, date)
  - GET /api/history/<id> — detail sesi + daftar video
  - GET /api/history/recent — riwayat terbaru (panel kanan Upload)
  - GET /api/history/stats — statistik hari ini (dinamis dari DB)
- [x] Halaman History (`static/app.js` modul History):
  - Tabel: waktu, HP, akun, folder, jumlah video, status
  - Filter: dropdown HP → dropdown akun (ter-update sesuai HP), tanggal
  - Reset filter
  - Klik baris → modal detail sesi + daftar video + timestamp
  - Empty state saat belum ada riwayat
- [x] Panel "Riwayat Upload" di halaman Upload (panel kanan) terisi:
  - 5 sesi terbaru, format waktu relatif (baru saja / 5m lalu / jam / Kemarin / tgl)
- [x] Statistik hari ini **dinamis** (sebelumnya statis):
  - Upload hari ini, Akun selesai, Sesi aktif, HP online
- [x] Helper waktu: formatDateTime, formatRelativeTime, parseSqlDate (UTC→lokal)
- [x] Auto-refresh history & stats setelah sesi upload selesai/konfirmasi
- [x] **Teruji:** list, filter (HP/akun/tanggal), detail, recent, stats,
      rantai workflow→history→stats real-time, server nyata port 5001 OK
- [x] **ZIP:** `remote-hp-v1.04.zip`

**Yang sudah bisa dipakai di v1.04:**
- Halaman History lengkap dengan filter & detail per sesi
- Statistik hari ini yang update otomatis mengikuti aktivitas upload
- Riwayat terbaru tampil di halaman utama (panel kanan)
- Semua data tersambung real-time dari workflow upload

---

### v1.05 — Settings & Polish 🔜 (checkpoint terakhir)
- [ ] Caption template CRUD (tambah/edit/hapus/aktif-nonaktif) di Pengaturan
- [ ] Halaman Pengaturan lengkap:
  - Manajemen template caption
  - Jam posting default & rentang
  - Path storage, path ADB, folder target HP
  - Backup database (download .db)
- [ ] Tombol simpan pengaturan + load nilai tersimpan
- [ ] Polish UI + edge cases akhir
- [ ] README final + ZIP: `remote-hp-v1.05.zip`

---

## 🎯 ATURAN KETAT — 🎉 SEMUA 10 AKTIF & TERUJI (sejak v1.02)

Aturan 1–10 dari masterplan semua sudah aktif & teruji end-to-end.
(Detail tabel ada di checkpoint v1.02/v1.03.)

---

## 🛠️ STACK
- Backend: Python + Flask
- Database: SQLite (`remote_hp.db`, auto-generate)
- Frontend: HTML + Vanilla JS (app.js + upload.js)
- ADB: subprocess (cross-platform)
- Port: **5001**

---

## 🗂️ STRUKTUR FILE (saat ini)

```
remote-hp/
├── setup-windows.bat       ✅ setup 1-klik Windows
├── jalankan-windows.bat    ✅ run Windows
├── setup-ubuntu.sh         ✅ setup 1x Ubuntu/Linux
├── jalankan-ubuntu.sh      ✅ run Ubuntu/Linux
├── CARA-SETUP.md           ✅ panduan pemula
├── .gitignore              ✅
├── app.py                  ✅
├── requirements.txt        ✅
├── README.md               ✅
├── PROGRES.md              ✅
├── database/
│   ├── db.py               ✅
│   └── schema.sql          ✅
├── routes/
│   ├── devices.py          ✅ CRUD + status/detect ADB
│   ├── accounts.py         ✅ CRUD
│   ├── upload.py           ✅ workflow FIFO (11 endpoint)
│   ├── history.py          ✅ list/detail/recent/stats
│   └── settings.py         ✅ settings + jadwal (caption CRUD → v1.05)
├── services/
│   ├── adb.py              ✅
│   ├── folder.py           ✅
│   ├── guard.py            ✅
│   ├── caption.py          ✅
│   └── scheduler.py        ✅
├── static/
│   ├── app.js              ✅ + modul History & Jadwal
│   ├── upload.js           ✅ wizard workflow
│   └── style.css           ✅
└── templates/
    └── index.html          ✅
```

---

*Dokumen ini diupdate setiap checkpoint.*
