# v1.22.1 — Video Mixer, pengaman 30.000, dan metadata waktu lokal

- Nama tampilan aplikasi diubah dari **Video Matrix Generator** menjadi **Video Mixer**.
- ID internal Remote Server tetap `matrix_generator`; aktivasi dan laporan lama tetap kompatibel.
- Default tetap **Tanpa limit** dan tidak ada batas maksimum permanen.
- Backend menghitung ulang jumlah output; di atas 30.000 video, UI menampilkan popup konfirmasi sebelum job dibuat.
- Konfirmasi terikat pada konfigurasi aktif. Perubahan grid, mode, audio, profil output, atau limit membatalkan konfirmasi lama.
- Nama image/container menjadi `video-mixer:1.22.1` dan `video_mixer_app`; volume aktivasi lama tetap dipakai.
- Folder output dan laporan menyimpan waktu lokal browser serta zona waktu client untuk sinkronisasi dashboard Remote Server berikutnya.

# Changelog

## v1.22.1 — 2026-08-06

- Mengganti label ukuran **Vertical** menjadi **Track** dan **Horizontal** menjadi **Clip** pada antarmuka Setup.
- Mengganti nama mode yang tampil kepada pengguna: **Acak per Track**, **Acak Lintas Track**, **Urutan Clip**, dan **Urutan Clip — Track Unik**.
- Menyamakan nama mode pada panel Estimasi otomatis, panel Mode kombinasi, dan estimasi ukuran output.
- Internal key mode, API, kalkulator kombinasi, struktur folder output, job manager, dan pipeline FFmpeg tidak diubah.

## v1.21.0 — 2026-08-06

- Menata ulang panel **Setup matriks** menjadi dua kolom: kontrol ukuran di kiri dan Estimasi otomatis di kanan.
- Mengurutkan kontrol ukuran secara vertikal: **Vertical** di atas dan **Horizontal** di bawah.
- Menghapus tombol manual Upload pada audio eksternal. File audio Replace/Mix kini langsung diunggah setelah dipilih, termasuk pilihan banyak file.
- Menambahkan status proses unggah otomatis, hasil berhasil/gagal, serta tetap memuat ulang daftar audio dan penggunaan storage.
- Tidak mengubah endpoint upload audio, kalkulator kombinasi, job manager, Remote Server client, atau pipeline FFmpeg.

## v1.20.0 — 2026-08-06

- Menambahkan tombol **Bersihkan audio** pada menu Storage & pemeliharaan.
- Memastikan **Bersihkan semua** tetap menghapus `uploads`, `outputs`, `temp`, dan `audio`.
- Menghapus ringkasan matriks dari header.
- Menghapus indikator status **SIAP/RENDER** dari header.
- Menghapus badge permanen Remote Server dari header tanpa mengubah validasi akses, mode offline, banner, atau overlay blokir.
- Engine kombinasi, job manager, dan pipeline FFmpeg tidak diubah.

## v1.19.0 — 2026-08-06

- Memindahkan **Storage & pemeliharaan** dari tab Setup ke menu ringkas pada header.
- Mempertahankan seluruh fungsi pemilihan folder, informasi penggunaan storage, refresh, dan pembersihan file.
- Menghapus kartu Storage dari alur Setup sehingga ruang kerja matriks lebih fokus.
- Meratakan empat kartu **Mode kombinasi** dalam layout 2×2 dengan tinggi konsisten.
- Mengubah informasi **Maksimum video hasil** menjadi metadata datar dengan divider, tanpa subpanel bersarang.
- Tidak mengubah API, kalkulator kombinasi, job manager, Remote Server client, atau pipeline FFmpeg.

## v1.18.0 — 2026-08-06

- Menghapus label **LOCAL VIDEO WORKSPACE** dan kalimat pengantar di area judul.
- Menghapus judul dan deskripsi berulang pada panel Setup matriks.
- Menghapus judul dan deskripsi panel estimasi otomatis, tanpa menghapus nilai estimasi empat mode.
- Menghapus footer informasi versi/render dari halaman utama.
- Menyembunyikan hint kesiapan setelah grid lengkap.
- Menghapus ringkasan teks setelah upload massal baris/kolom; status setiap sel dan progress grid tetap bekerja.
- Merapikan jarak antarkomponen setelah copy dihapus.
- Tidak mengubah API, kalkulator kombinasi, job manager, Remote Server client, atau pipeline FFmpeg.

## v1.17.0 — 2026-08-06

- Menghapus kartu ringkasan **Grid**, **Total sel**, **Terisi**, **Klip/output**, dan **Kalkulasi** dari panel Setup matriks.
- Merapikan pilihan Horizontal dan Vertical agar tidak menyisakan kolom kosong setelah kartu ringkasan dihapus.
- Status jumlah sel terisi tetap tersedia pada toolbar Matriks upload.
- Estimasi maksimum seluruh mode kombinasi dan kalkulasi otomatis tetap dipertahankan.
- Tidak mengubah API, kalkulator kombinasi, job manager, Remote Server client, atau pipeline FFmpeg.

## v1.16.0 — 2026-08-06

- Memperbesar tombol upload massal pada header kolom menjadi tombol persegi panjang horizontal.
- Memperbesar tombol upload massal pada header baris menjadi tombol persegi panjang vertikal.
- Memperbesar tombol `+` upload individual di setiap sel menjadi tombol persegi yang terlihat jelas.
- Menambahkan state hover dan keyboard focus yang lebih kuat agar target klik mudah dikenali.
- Mempertahankan matriks penuh 1×1 sampai 10×10 tanpa scroll internal serta tidak mengubah API, kalkulator kombinasi, job manager, atau pipeline FFmpeg.

## v1.15.0 — 2026-08-06

- Menata empat pilihan Mode kombinasi menjadi grid 2 × 2 pada layar desktop.
- Menghapus seluruh deskripsi tambahan pada kartu Mode kombinasi; kartu kini fokus pada nama, status, dan maksimum video hasil.
- Menghapus scroll internal pada Matriks upload. Seluruh grid 1×1 sampai 10×10 tampil sebagai satu bidang utuh dan mengikuti lebar panel.
- Menghilangkan ruang kosong kanan pada matriks dengan kolom fraksional yang mengisi 100% lebar tersedia.
- Tidak mengubah API, kalkulator kombinasi, job manager, maupun pipeline FFmpeg.

## v1.14.0 — 2026-08-06

- Membatasi matriks menjadi maksimum 10 × 10 pada UI dan validasi API.
- Menghapus pilihan tampilan Pas, Padat, dan Nyaman; matriks kini memakai layout otomatis.
- Menata tab Render menjadi dua kolom tetap: kiri Kualitas output → Folder output → Performa; kanan Audio & encoder → Jumlah output → Mode kombinasi.
- Mendesain ulang kartu Mode kombinasi agar status dan maksimum video hasil jauh lebih mudah dibaca.
- Tidak mengubah generator kombinasi maupun pipeline FFmpeg.

## 1.13.0

- Menjadikan **Tanpa limit** sebagai pilihan default pada panel Jumlah output. Batch manual tetap tersedia dan otomatis memakai nilai awal 100 ketika diaktifkan.
- Menjadikan metode render **Klasik** sebagai pilihan default di antarmuka dan payload frontend, tanpa mengubah fallback atau implementasi engine FFmpeg.
- Menambahkan estimasi otomatis jumlah maksimum video untuk keempat mode kombinasi langsung pada panel **Setup matriks**.
- Estimasi Setup diperbarui setiap kali nilai Horizontal atau Vertical berubah, lengkap dengan status Valid/Tidak valid untuk ukuran grid aktif.
- Kartu mode pada tab Render tetap menampilkan angka yang sama untuk membantu pemilihan mode; endpoint `/api/calc` dan kalkulator backend tidak diubah.
- Versi client dinaikkan menjadi 1.13.0.

## 1.12.0

- Menyederhanakan workflow antarmuka dari empat tab menjadi hanya **Setup** dan **Render** tanpa mengubah endpoint, payload, kalkulator backend, job manager, atau proses FFmpeg.
- Menggabungkan pemilihan ukuran matriks dan seluruh fungsi upload ke tab **Setup**.
- Menghapus langkah UI **Output**, panel Struktur output, tabel estimasi terpisah, serta tombol manual “Hitung estimasi”.
- Endpoint `/api/calc` tetap dipertahankan dan sekarang dipanggil otomatis saat ukuran Horizontal/Vertical berubah.
- Menambahkan ringkasan real-time pada Setup dan Render: ukuran grid, total/sel terisi, jumlah klip per output, dan status kalkulasi.
- Menampilkan validitas dan jumlah maksimum kombinasi langsung pada setiap kartu mode di tab Render.
- Tab Render baru terbuka setelah seluruh sel terisi dan kalkulasi otomatis berhasil; engine tetap menghitung ulang rencana job saat Generate.
- Menjadikan **Dengan limit** sebagai pilihan default dengan batch size 100 untuk menekan risiko render kombinasi ekstrem secara tidak sengaja. Opsi Tanpa limit tetap tersedia.
- Memadatkan pengaturan storage menjadi panel utilitas yang dapat dibuka-tutup agar area utama Setup berfokus pada matriks dan upload.
- Versi client dinaikkan menjadi 1.12.0.

## 1.11.0

- **Redesain UI/UX penuh tanpa mengubah engine render**: endpoint, payload, kalkulasi kombinasi, proses upload, dan alur FFmpeg tetap dipertahankan.
- Layout diubah menjadi **workspace full-width** agar area kanan-kiri monitor tidak terbuang.
- Navigasi pipeline vertikal diganti menjadi **tab horizontal**: Setup, Upload, Output, dan Render, lengkap dengan status Terkunci/Siap/Selesai.
- Grid upload diubah menjadi tampilan **spreadsheet padat**. Klik sel menampilkan detail file; klik dua kali, tombol `+`, atau drag-and-drop digunakan untuk memilih video.
- Menambahkan tiga kepadatan grid: **Pas**, **Padat**, dan **Nyaman**. Mode Pas menghitung lebar sel dari viewport sehingga matriks 20×20 dapat tampil penuh secara horizontal pada monitor lebar tanpa membuat halaman overflow.
- Header baris/kolom tetap sticky dan fungsi upload massal per baris/kolom tetap tersedia.
- Menambahkan indikator jumlah sel terisi, progress bar upload, panel detail sel, dan ringkasan ukuran matriks pada topbar.
- Panel Render disusun dua kolom pada layar lebar agar lebih ringkas, tetapi tetap responsif pada layar kecil.
- Memperbaiki label versi antarmuka yang sebelumnya masih menampilkan versi lama.
- Versi client dinaikkan menjadi 1.11.0.

## 1.10.0

- **Grid upload diperbesar: 10×10 → 20×20** (maks. 400 sel). Sel otomatis
  memakai tampilan "compact" (lebih kecil, ikon & teks ringkas) begitu
  salah satu sisi grid melebihi 10, supaya tetap nyaman di-scroll.
- **Upload massal per baris & kolom**: setiap baris (huruf) dan kolom
  (angka) kini punya tombol upload di header grid. Klik → pilih banyak
  file video sekaligus (multi-select) → otomatis mengisi sel-sel baris/
  kolom itu sesuai urutan file dipilih. File berlebih (melebihi panjang
  baris/kolom) diabaikan dengan info jumlah yang di-skip; sisa sel yang
  belum terisi tetap bisa diisi manual satu per satu seperti biasa.
- **Mode audio baru: Replace & Mix** (v1.9 sebelumnya cuma Mute/Keep,
  default tetap Mute):
  - **Replace** — audio asli seluruh klip dibuang, diganti 1 track audio
    eksternal yang membentang utuh di sepanjang 1 video hasil generate
    (bukan per klip).
  - **Mix** — audio asli klip dipertahankan, digabung (mix) dengan 1 track
    audio eksternal yang membentang di sepanjang output. Volume dibiarkan
    natural, tanpa normalisasi/EQ apa pun.
  - Upload audio eksternal mendukung 1–n file (unlimited), UI ringkas
    (badge angka + modal "Lihat daftar" agar tidak memenuhi layar meski
    ada ratusan file).
  - Bila lebih dari 1 file audio diupload: dipakai **rolling round-robin**
    per output video (bukan per klip) — output ke-1 → audio ke-1, ke-2 →
    audio ke-2, dst, lalu berulang dari awal. Urutan ini dijamin
    deterministik meski render berjalan dengan banyak worker paralel.
  - Durasi: audio lebih panjang dari video → ujungnya dipotong mengikuti
    panjang video. Audio lebih pendek → sisa durasi video dibiarkan hening
    di akhir (audio TIDAK di-loop).
  - Endpoint baru: `POST /api/upload_audio`, `GET /api/audio_list`,
    `DELETE /api/audio_delete`, `DELETE /api/audio_clear`. Folder storage
    baru: `storage/audio/`.
  - Secara teknis: Replace/Mix menambah 1 tahap render tambahan setelah
    video selesai digabung (video hasil gabungan selalu memakai audio asli
    klip di tahap ini, setara mode "keep"), lalu ditempel/di-mix ulang
    dengan audio eksternal — video di-copy (tanpa re-encode ulang) di
    tahap tambahan ini.
- Versi client dinaikkan menjadi 1.10.0.

## 1.9.0

- **Perubahan mode kombinasi (breaking):** mode `Vertikal` dan `Campuran
  Vertikal` dihapus. Fokus aplikasi kini sepenuhnya pada keluarga
  "Horizontal" (urutan kolom = angka 1..H, isi tiap kolom = huruf/baris).
- Menambahkan mode baru **Campuran Horizontal — Linear**: baris bebas
  dipilih per kolom (boleh berulang), tetapi urutan tampil klip di output
  SELALU mengikuti urutan kolom asli (1→2→3→...→H), tidak diacak.
  Rumus: `v^h`.
- Menambahkan mode baru **Campuran Horizontal — Linear Unik**: sama seperti
  Linear, tetapi huruf/baris tidak boleh berulang dalam 1 output (mis.
  tidak ada `A1+A2+...`). Rumus: `v! / (v-h)!` (nPk), hanya valid bila
  jumlah baris (v) ≥ jumlah kolom (h).
- Mode `Campuran Horizontal` (lama, urutan tampil diacak bebas dengan
  faktor `h!`) tetap dipertahankan sebagai pilihan terpisah.
- UI "Struktur output" dan "Mode kombinasi" diperbarui: 4 pilihan
  (Horizontal, Campuran Horizontal, Campuran Horizontal — Linear, Campuran
  Horizontal — Linear Unik). Rule saling-eksklusif Horizontal↔Campuran
  Horizontal dan Vertikal↔Campuran Vertikal dihapus; sekarang semua mode
  independen dan boleh dikombinasikan bebas (selama valid untuk ukuran
  grid saat ini).
- Nama folder output baru: `campuran_horizontal_linear/` dan
  `campuran_horizontal_linear_unik/`.
- Versi client dinaikkan menjadi 1.9.0.

## 1.8.1

- Memperbaiki kegagalan startup Windows: `docker-compose.yml` tidak lagi memaksa device Linux `/dev/dri`.
- Perintah standar `docker compose up -d --build` sekarang berjalan di Docker Desktop dengan fallback CPU.
- Menambahkan `docker-compose.gpu.yml` khusus Linux VAAPI; `run.sh` memilihnya otomatis bila GPU tersedia.
- Menghapus bind mount `/etc/machine-id` yang tidak portabel di Windows.
- Fingerprint komputer kini memakai host ID acak yang persisten di volume `video_matrix_client_data`.
- Menambahkan `run-windows.bat` dan `stop-windows.bat`.
- Versi client dinaikkan menjadi 1.8.1.

## 1.8.0

- Integrasi aktivasi dengan Remote Server `https://remote.darda.uk`.
- Token dan sesi persisten di volume Docker.
- Fingerprint memakai machine-id komputer host, bukan ID container.
- Single session, heartbeat, session close, grace period 3 jam, revoke, dan conflict handling.
- Halaman aktivasi dan overlay pemblokiran saat akses dicabut.
- Render aktif dihentikan otomatis setelah revoke/conflict terdeteksi.
- Laporan `generate_completed` dikirim setelah job selesai tanpa mengirim file video.
- Port web dibatasi ke `127.0.0.1:5000`.
- Health check publik baru `/api/health` agar container tetap healthy sebelum aktivasi.
- Image dan dependency build memverifikasi Flask, Waitress, dan Requests.
- Seluruh fungsi render v1.7 dipertahankan.

# Video Matrix Generator — v1.7

Fokus rilis: **perbaikan bug FREEZE acak pada metode render "Cepat"** (concat
tanpa re-encode). Sebagian output bisa freeze di posisi & durasi acak
(awal/tengah/akhir, sebentar sampai beberapa klip), paling sering saat memakai
encoder GPU (VAAPI/NVENC). Tidak ada perubahan pada kontrak folder/penamaan
output maupun fitur "Kualitas output" dari v1.6.

## A. Akar masalah

Pada metode "Cepat", tiap output disusun dengan **concat demuxer** memakai file
daftar yang menuliskan `duration` (panjang) setiap potongan secara eksplisit.
Sampai v1.6 panjang itu dihitung dari **metadata `nb_frames`** (jumlah frame di
header MP4): `duration = nb_frames / fps`.

- Untuk **libx264 (CPU)** metadata `nb_frames` selalu tepat, jadi sambungan
  mulus — sebab itu bug ini tidak muncul di pengujian CPU.
- Untuk **encoder HARDWARE (VAAPI/NVENC)** dan sebagian muxer, `nb_frames`
  kadang **salah atau kosong**. Bila `duration` yang ditulis **lebih besar**
  dari panjang potongan sebenarnya, concat demuxer menyisakan **celah** di
  sambungan → frame terakhir potongan itu **ditahan (freeze)** selama
  selisihnya. Bila **lebih kecil**, potongan berikutnya mulai lebih awal →
  frame drop. Karena tiap klip bisa meleset berbeda-beda, freeze tampak **acak**
  posisi & durasinya.

Ini dikonfirmasi lewat uji terkontrol: `duration` yang meleset **+2 frame**
menghasilkan freeze **0,125 dtk di setiap sambungan**; tanpa directive atau
dengan jumlah frame eksak, hasilnya mulus sempurna.

## B. Perbaikan

1. **Durasi potongan dari jumlah frame EKSAK (dekode), bukan metadata.**
   Fungsi baru `_probe_frames_accurate()` memakai `ffprobe -count_frames`
   (`nb_read_frames`) yang **benar-benar mendekode & menghitung** frame,
   sehingga **selalu tepat untuk encoder apa pun** (termasuk VAAPI/NVENC).
   Dijalankan **sekali per klip unik** (bukan per output), jadi biayanya kecil.
   Bila gagal, jatuh ke metadata lama lalu ke "tanpa directive".

2. **File perantara dipaksa CFR sempurna mulai dari nol.** Filter normalisasi
   kini diakhiri `setpts=N/fps/TB` sehingga timestamp tiap frame tepat `N/fps`
   dari 0 — menghilangkan sisa offset/jitter dari sumber VFR (video HP) atau
   dari encoder hardware.

3. **Tanpa edit-list / delay awal di file perantara.** Ditambah
   `-avoid_negative_ts make_zero`, `-muxpreload 0`, `-muxdelay 0` saat menulis
   file perantara MP4, supaya tidak ada pergeseran presentasi yang menyisakan
   celah di sambungan copy.

Untuk **libx264 (CPU)** hasilnya identik dengan sebelumnya (sudah rapi); untuk
**encoder hardware** inilah yang menghilangkan freeze.

## C. Verifikasi

- **Reproduksi akar masalah**: dibuktikan directive `duration` yang meleset
  menimbulkan freeze di sambungan, dan jumlah frame eksak menghilangkannya.
- **Metadata rusak**: pada file dengan `nb_frames` kosong (meniru muxer
  hardware), jalur lama menulis durasi kosong (berisiko celah) sedangkan
  `_probe_frames_accurate` tetap mengembalikan jumlah frame yang benar.
- **Pipeline "fast" penuh** dengan sumber menyulitkan (VFR seperti video HP,
  durasi ganjil, resolusi campuran, sebagian tanpa audio): **bebas celah** dan
  **tanpa frame beku** untuk kasus mute, ber-audio, dan berbagai fps (24/30).
- **Uji integrasi Flask end-to-end** metode "Cepat" (6 output, worker paralel):
  semua file resolusi benar, **tanpa celah timestamp**, dekode bersih.

## D. Kompatibilitas

- Tidak ada perubahan API, struktur folder, atau penamaan `video_0001.mp4`.
- Semua opsi v1.6 (Kualitas output, resolusi/fps/CRF/bitrate) tetap sama.
- Metode **Klasik** (re-encode penuh) tidak berubah dan tetap jadi fallback
  otomatis per-output bila remux gagal.

---

# Video Matrix Generator — v1.6

Fokus rilis: **fitur baru "Kualitas output"** — resolusi, frame rate, dan
bitrate/CRF kini dapat dipilih dari UI, dengan **default disetel setara sumber
720p** yang umum dipakai. Sampai v1.5 profil output di-*hardcode* ke
1080×1920 @30fps CRF20, sehingga sumber 720p bitrate rendah selalu di-*upscale*
dan menghabiskan waktu render serta ruang disk berlebih. Tidak ada perubahan
kontrak folder/penamaan output — payload lama tetap berjalan (kompatibel
mundur, otomatis memakai default 720p).

## A. FITUR UTAMA: panel "Kualitas output" (resolusi / fps / bitrate)

Panel baru di langkah Render dengan kontrol:

- **Preset cepat**: *Setara sumber 720p @24fps* (default), *Seimbang 1080p
  @30fps*, *Maksimal 1080p @30fps kualitas tinggi*, atau *Kustom*. Preset hanya
  mengisi kontrol detail; kontrol detail tetap sumber kebenaran yang dikirim ke
  backend. Mengubah kontrol manual otomatis memindah preset ke *Kustom*.
- **Resolusi**: 540×960, 720×1280 (default), 1080×1920, 1440×2560, atau
  **Kustom (Lebar × Tinggi)**. Dimensi ganjil dibulatkan ke genap (syarat
  H.264 yuv420p).
- **Frame rate**: 24 (default), 25, 30, 50, 60 fps.
- **Kontrol bitrate**: *Kualitas tetap (CRF)* — default — atau *Bitrate target*.
  - CRF: pilihan 18–28 (default **23**, setara sumber).
  - Bitrate target: input kbps (default **2000**), di-encode VBR terbatas
    (`-b:v` + `-maxrate` + `-bufsize`).
- **Bitrate audio**: input kbps (default **128**, turun dari 192), tampil hanya
  saat suara tidak di-mute.

**Kenapa default 720p @24fps CRF23?** Sumber vertikal umum sudah 720×1280,
24fps, ~2 Mbps. Default baru menyamai itu: **tidak ada upscale, tidak ada
bitrate berlebih**. Pada uji render dengan konten identik, output default baru
**±67% lebih kecil** dari default lama 1080p CRF20, dan lebih cepat karena tiap
klip tidak lagi di-scale naik.

## B. Backend: profil output konfigurabel (dulu konstanta global)

- Konstanta `TARGET_W/H/FPS/AR/AC/TIMESCALE` yang di-*hardcode* di
  `ffmpeg_worker.py` diganti kelas **`OutputProfile`** yang divalidasi &
  di-*clamp* (dimensi genap 16–4320, fps 1–120, CRF 0–51, bitrate dalam batas
  aman). Semua pembangun perintah ffmpeg (normalisasi, remux, concat klasik)
  kini memakai profil ini.
- **Timescale mp4 diturunkan dari fps** (`512 × fps`) alih-alih tetap 15360.
  Ini menjaga matematika sambungan *concat copy* tetap eksak untuk fps berapa
  pun (tiap frame tepat 512 tick) — sehingga metode **Cepat** tetap mulus tanpa
  freeze di 24/25/30/50/60 fps. Diverifikasi: hasil 720p @24 dan 1080p @30
  dekode penuh tanpa error DTS.
- **Dua mode rate-control** untuk ketiga encoder (libx264 / NVENC / VAAPI):
  CRF/CQ/QP (kualitas tetap) atau bitrate target (VBR terbatas).
- **Audio**: sample rate default 48 kHz (mengikuti sumber, menghindari
  resample), bitrate default 128 kbps — keduanya mengikuti profil.
- Profil aktif dicatat di **log render** (mis. `Profil output: 720x1280
  @24fps · CRF 23 · mute`) dan dikembalikan di `meta.outputProfileActive`.

## C. Estimasi ukuran mengikuti profil

`/api/estimate_size` tidak lagi mengasumsikan ~8 Mbps @1080p tetap. Bitrate
estimasi kini diturunkan dari profil terpilih:

- Mode *Bitrate target*: memakai angka bitrate langsung (akurat).
- Mode *CRF*: heuristik bits-per-pixel-per-frame (CRF 23 @720p24 ≈ 2 Mbps;
  tiap −6 CRF ≈ 2× bitrate), cenderung sedikit lebih besar (aman).

Teks asumsi di UI (dulu selalu "1080×1920 @30fps ~8 Mbps · audio 192 kbps")
kini menampilkan resolusi/fps/bitrate/mode yang sebenarnya dipilih. Footer juga
menampilkan profil aktif dan ikut berubah saat pengaturan diubah.

## D. Kompatibilitas mundur

- Payload `/api/start` tanpa `outputProfile` otomatis memakai default 720p
  @24fps CRF23 (diverifikasi end-to-end).
- Struktur folder `outputs/<run_tag>/<mode>/<bundle>/video_0001.mp4` dan
  penamaan berurutan **tidak berubah** — aplikasi pendamping tetap kompatibel.
- Konstanta `EST_VIDEO_BITRATE_BPS` / `EST_AUDIO_BITRATE_BPS` tetap diekspor
  (nilai diperbarui ke default 720p) demi kompatibilitas import.

## E. Verifikasi

- **Uji integrasi Flask end-to-end**: `/api/system` (v1.6.0), `/api/estimate_size`
  (asumsi mengikuti profil), lalu `/api/start` → render → cek file hasil.
- Semua jalur render diuji dan file hasil dedekode tanpa error:
  Cepat + CRF + 720p; Klasik + bitrate target + 1080p + audio; dan
  backward-compat (tanpa profil → 720p default).
- Sumber campuran (resolusi/fps berbeda, sebagian tanpa audio) dinormalisasi
  mulus ke profil target.

---

# Video Matrix Generator — v1.5

Fokus rilis: **perbaikan bug** — terutama panel *Performa* yang ternyata tidak
berfungsi — plus penuntasan wiring UI v1.4, penguatan stabilitas, dan
pembersihan dead file. Tidak ada perubahan kontrak API maupun struktur output;
payload lama tetap berjalan (kompatibel mundur).

## A. FIX UTAMA: panel "Performa" (Metode render & Worker paralel) tidak berfungsi

Penyebab: `app.js` tidak pernah membaca elemen `#renderMethod` dan
`#parallelWorkers`, sehingga keduanya **tidak pernah dikirim** di payload
`/api/start`. Backend selalu jatuh ke default (`fast` / `auto`) — memilih
"Klasik" atau worker 1–4 di UI tidak berpengaruh apa pun.

Perbaikan: kedua nilai kini dibaca dan dikirim. Diverifikasi end-to-end:
`renderMethodActive` dan `parallelWorkersActive` di status job mengikuti
pilihan UI (classic + worker 2 benar-benar aktif).

## B. Elemen UI v1.4 yang belum pernah terhubung kini aktif

- **Chip sistem** di topbar dulu selamanya "memeriksa sistem…" karena
  `/api/system` tidak pernah dipanggil frontend. Kini menampilkan encoder
  terdeteksi (NVENC/VAAPI/CPU), jumlah thread, dan worker Auto; hint encoder
  di Panel 5 ikut menampilkan hasil deteksi.
- **Chip tahap**: "Tahap 1/2 — Normalisasi x/y" dan "Tahap 2/2 — Render"
  kini tampil (data `phase`/`prep` dari backend selama ini dibuang frontend).
- **Bar progres global besar** dulu selalu 0% karena tidak pernah di-update;
  saat tahap normalisasi bar mengikuti progres normalisasi.
- **Lokasi folder hasil** (`meta.outputDir`) ditampilkan setelah job
  selesai/dihentikan.
- **ETA** diformat `1j 23m 45d` dan (backend) kini **dibagi jumlah worker
  paralel** — sebelumnya ETA membengkak N kali saat memakai N worker.

## C. Stabilitas

- **ffmpeg runner anti-deadlock**: stderr kini dikuras thread latar dan stdout
  dibuang ke DEVNULL. Dulu keduanya PIPE tetapi baru dibaca setelah proses
  selesai — input korup yang memuntahkan ribuan baris error bisa memenuhi
  buffer pipe OS, ffmpeg terblokir menulis, dan job menggantung selamanya
  (Stop pun tidak bersih).
- **Exception tak terduga di worker paralel** kini ditangkap & dicatat di log.
  Dulu future `pool.submit()` menelannya diam-diam → counter tidak naik, bar
  progres macet di bawah 100%, output "hilang" tanpa jejak.
- **Registry job dilindungi lock** — waitress multi-thread; dua `/api/start`
  bersamaan bisa memicu `RuntimeError: dictionary changed size during
  iteration` saat pemangkasan riwayat.
- **`/api/storage/clean` ditolak (409) selama render berjalan** — dulu bisa
  menghapus uploads/temp di tengah job dan merusak render aktif.
- **Polling status tahan gangguan**: satu fetch gagal (server restart /
  jaringan putus sesaat) tidak lagi menghentikan polling dan mengunci UI
  selamanya; `Generate` juga membuka kunci UI kembali bila server tidak
  terjangkau.

## D. Dead file & kebersihan paket

- **`app/storage_config.json` dihapus dari paket** — artefak runtime berisi
  `{"storageBase": "/app/storage"}`. Bila proyek dijalankan native (tanpa
  Docker), app start dengan mencoba membuat `/app/storage` →
  PermissionError di Linux non-root / folder nyasar `C:\app\storage` di
  Windows. File ini dibuat otomatis saat user mengganti folder penyimpanan
  dan memang tidak boleh ikut distribusi.
- **`compose.txt` dihapus** — duplikat; seluruh isinya sudah ada di README.
- **`CHANGELOG-v1.1.md` dihapus** — 100% duplikat bagian v1.1 di CHANGELOG.md.
- **`Vidio Mixer.bat` dihapus** — shortcut pribadi (`start
  http://localhost:5000`), tidak dirujuk dokumentasi mana pun.
- Rapi-rapi kecil: `import time` normal di `app.py` (mengganti hack
  `__import__('time')`), anotasi `Dict[str, any]` menjadi `Dict[str, Any]`,
  label tombol "Muat ulang" konsisten dengan HTML, kapitalisasi label
  estimasi ukuran diseragamkan.

## E. Verifikasi rilis ini

Diuji end-to-end pada build ini (21 pengujian, semua lulus): upload → calc →
job **classic (worker 2)** dan **fast (worker 1)** masing-masing menghasilkan
6 output 1080×1920 valid; jumlah frame fast == classic (visual identik);
decode bersih tanpa error; klip tanpa audio mendapat injeksi track sunyi
(output tetap ber-audio); **STOP** menghentikan proses < 1 detik — video yang
selesai tetap ada, file setengah jadi & temp dibersihkan; guard clean 409
selama render, kembali diizinkan setelah selesai.

---

# Video Matrix Generator — v1.4

Fokus rilis: **kecepatan render, stabilitas jangka panjang, dan redesain UI menyeluruh**.
Dioptimalkan & diuji untuk mesin tanpa GPU diskrit (contoh: AMD Ryzen 5 5600G — iGPU
Radeon Vega, 6C/12T, RAM 15 GB, Ubuntu 24.04), tetap kompatibel untuk mesin lain.

## A. Render jauh lebih cepat: metode "Cepat" (normalisasi 1× + gabung tanpa re-encode)

Masalah lama: setiap output me-re-encode ulang klip sumber yang sama. Batch
6.000 output dari 4–100 klip berarti klip yang sama di-decode + di-scale +
di-encode ribuan kali.

Solusi v1.4 (dropdown **Metode render** di Panel 6, default **Cepat**):
- **Tahap 1** — tiap klip UNIK dinormalisasi SEKALI (1080×1920, 30 fps CFR,
  SAR 1, yuv420p, GOP 1 detik, timescale seragam) ke file perantara.
- **Tahap 2** — tiap output digabung dari file perantara memakai concat
  demuxer dengan `-c:v copy` (remux; nyaris secepat kecepatan disk).

Kenapa tidak freeze seperti dulu? Freeze lama terjadi karena stream-copy pada
sumber yang TIDAK seragam. Di sini semua segmen keluaran encoder yang sama
dengan parameter identik dan tiap file diawali keyframe IDR — sambungan
kontinu. Diverifikasi dengan test: jumlah frame output metode Cepat ==
metode Klasik, decode bersih tanpa error.

Untuk batch besar dampaknya dramatis: kerja encode turun dari
(jumlah output × klip per output) menjadi (jumlah klip unik). Semakin banyak
output, semakin besar percepatannya.

- Audio (bila tidak mute): video tetap copy, audio di-encode ulang AAC saat
  remux (sangat murah) supaya timestamp antar segmen rapat.
- Perbaikan perilaku: klip tanpa audio kini disuntik track sunyi saat
  normalisasi, sehingga output tetap ber-audio (dulu: satu klip bisu membuat
  SEMUA output kehilangan audio).
- **Fallback berlapis**: bila remux gagal untuk sebuah output → otomatis
  re-encode penuh (metode Klasik) untuk output itu; bila encoder GPU gagal →
  retry CPU (mekanisme v1.1.2 dipertahankan). Metode **Klasik** juga tetap
  bisa dipilih manual dari UI.
- File perantara ditulis di `temp/<job>/` dan SELALU dibersihkan di akhir
  (selesai, error, maupun Stop).

## B. Worker paralel + batas thread

Dropdown **Worker paralel** (Auto / 1–4). Auto ≈ 1 worker per 6 thread CPU
(Ryzen 5 5600G 12 thread → 2 worker). Saat paralel, tiap proses ffmpeg
dibatasi `-threads` supaya total tidak oversubscribe. Penomoran file tetap
deterministik (`video_0001.mp4`, …) karena indeks ditetapkan saat antre.
Generator kombinasi tetap streaming (antrean terbatas) — batch jutaan output
tidak menggelembungkan RAM.

## C. VAAPI akhirnya benar-benar aktif di iGPU AMD (perbaikan penting)

Dua penyebab kenapa encode selama ini selalu jatuh ke CPU (ffmpeg ~800% CPU,
suhu CPU 79–80 °C) padahal 5600G punya hardware encoder H.264:

1. **Driver VAAPI tidak ada di image Docker.** `python:3.11-slim` + `ffmpeg`
   tidak menyertakan `mesa-va-drivers` (driver VA-API AMD). ffmpeg punya
   `h264_vaapi`, tetapi test encode selalu gagal → fallback CPU. Dockerfile
   kini memasang `mesa-va-drivers`, `intel-media-va-driver`, `libva-drm2`,
   dan `vainfo` (diagnosa: `docker exec video_matrix_app vainfo`).
2. **GID grup render di-hardcode 992.** Kini memakai variabel
   `${RENDER_GID}`; skrip baru `./run.sh` mendeteksinya otomatis dari
   `/dev/dri/renderD128` lalu menjalankan compose.

Dengan VAAPI aktif, tahap encode pindah ke iGPU: CPU jauh lebih dingin,
desktop tetap responsif, dan worker paralel makin efektif.

## D. Stabilitas server & proses

- **Server produksi (waitress)** menggantikan Flask dev server. `debug=True`
  lama menyalakan auto-reloader + werkzeug debugger — debugger tersebut bisa
  mengeksekusi kode arbitrer bila port 5000 terekspos ke jaringan/Tailscale.
- **Cache ffprobe** per (path, ukuran, mtime). Dulu deteksi audio dipanggil
  untuk tiap klip pada TIAP output — ribuan spawn ffprobe mubazir; estimasi
  ukuran ulang kini juga instan.
- **`nice -n 10`** untuk semua proses ffmpeg — render panjang tidak membuat
  desktop tersendat.
- **`init: true`** di compose (reap proses ffmpeg yatim — tidak ada zombie
  saat batch panjang), **healthcheck**, dan **`stop_grace_period: 30s`**.
- Riwayat job di memori dipangkas otomatis (15 job selesai terakhir).
- Flag `-vsync` (deprecated, dobel dengan `-fps_mode`) dihapus; `-nostdin`
  ditambahkan; `-video_track_timescale` diseragamkan.

## E. Redesain UI menyeluruh

Tampilan lama tumbuh bertahap dari banyak iterasi sehingga tidak konsisten.
v1.4 menulis ulang HTML + CSS dengan satu bahasa desain "konsol render":

- **Rail pipeline bernomor 01–06** — mencerminkan alur kerja bertahap yang
  memang terkunci berurutan; langkah nonaktif tampak redup, langkah aktif
  menyala amber.
- **Satu warna sinyal (amber)** untuk aksi/aktif/progres; merah hanya untuk
  aksi destruktif. Semua data (angka, path, log, badge) memakai monospace.
- **Topbar status**: chip encoder terdeteksi (GPU · VAAPI / CPU · libx264 +
  jumlah thread, dari endpoint baru `GET /api/system`) dan indikator
  SIAP / MERENDER.
- **Monitor render** baru: chip tahap (Tahap 1/2 Normalisasi → Tahap 2/2
  Render), statistik besar (selesai/total, %, perkiraan sisa dengan format
  jam-menit), progress bar global + per mode, log auto-scroll, dan lokasi
  folder hasil setelah selesai.
- **Notifikasi**: pesan aksi (terapkan storage, bersihkan folder, error)
  kini tampil sebagai bar notifikasi — sebelumnya ditulis ke elemen log yang
  tersembunyi sehingga tidak pernah terlihat.
- Ikon emoji diganti SVG (konsisten lintas OS), teks antarmuka dirapikan,
  fokus keyboard terlihat, menghormati `prefers-reduced-motion`, responsif
  sampai layar sempit.
- **Kontrak lama dipertahankan**: semua ID elemen, endpoint API, struktur
  folder output, penamaan file, dan kompatibilitas dengan aplikasi Remote HP
  tidak berubah.

## F. Berkas & cara pakai baru

- `run.sh` — start sekali jalan: deteksi GID GPU → build → up.
- `README.md` — dokumentasi ringkas instalasi, alur kerja, dan diagnosa GPU.
- `requirements.txt` + `waitress`; `docker/Dockerfile` + driver VAAPI;
  `docker-compose.yml` diperbarui (lihat bagian C & D).

**Payload API**: `POST /api/start` menerima field opsional baru
`renderMethod` ("fast"|"classic") dan `parallelWorkers` ("auto"|"1".."4").
Payload lama tanpa field ini tetap berfungsi (default fast + auto).

---

# Video Matrix Generator — v1.1.2

Tambahan di atas v1.1.1: **Hardware video encoding (GPU) dengan fallback CPU otomatis**.

## Baru: GPU Encoding (NVENC / VAAPI) + fallback otomatis ke CPU

Proses encode H.264 kini bisa memakai GPU sehingga generate batch jauh lebih
cepat & beban CPU turun. Logika matrix/grid/mode **tidak berubah** — filter
(scale/pad/setsar/fps/concat) tetap berjalan di CPU seperti sebelumnya; yang
dipindah ke GPU hanya tahap encode.

**Pilihan encoder (dropdown baru di Panel 5, di samping "Hapus Suara"):**
- **Auto (rekomendasi)** — deteksi otomatis dengan prioritas:
  `nvenc` (NVIDIA) → `vaapi` (AMD/Intel) → `cpu` (libx264).
- **GPU Nvidia (NVENC)** — `h264_nvenc -preset p4 -tune hq -rc vbr -cq 20 -b:v 0`.
- **GPU AMD/Intel (VAAPI)** — `h264_vaapi -qp 20` via `/dev/dri/renderD*`
  (frame di-upload ke GPU dengan `format=nv12,hwupload`).
- **CPU (paling kompatibel)** — `libx264 -preset veryfast -crf 20`
  (perilaku lama, tidak diubah).

**Deteksi yang jujur (bukan sekadar cek build ffmpeg):**
`detect_best_encoder()` menjalankan `ffmpeg -hide_banner -encoders` LALU
melakukan **test encode kecil** (beberapa frame dummy) untuk memastikan
driver + GPU benar-benar bisa dipakai — encoder yang terdaftar di build
belum tentu jalan (mis. `h264_nvenc` ada tapi driver NVIDIA tidak terpasang).
Hasil deteksi **di-cache per proses server** — tidak diulang tiap video/job.

**Transparan lewat log (tanpa buka terminal):**
Setiap job mulai, panel Progress menampilkan baris seperti:
- `Encoder terpilih: nvenc (NVIDIA GeForce RTX 3060)`
- `Encoder terpilih: vaapi (AMD/ATI — /dev/dri/renderD128)`
- `Encoder terpilih: cpu (libx264, GPU tidak terdeteksi)` + detail alasannya.

**Tahan banting (retry CPU per video):**
Jika encode GPU **gagal di tengah batch** (mis. driver error / GPU mendadak
tak bisa diakses), video tersebut otomatis di-**retry SEKALI memakai CPU**
sehingga batch tidak berhenti total. Kejadian ini dicatat di log
(`⚠ Encoder ... gagal ... — retry pakai CPU` lalu `✔ ... berhasil setelah
fallback ke CPU`). Video berikutnya tetap mencoba encoder GPU (error sesaat
tidak mematikan GPU permanen).

**Docker & akses GPU:**
`docker-compose.yml` kini meneruskan `/dev/dri` ke container (`devices:`)
dan menambah `group_add` supaya user `1000:1000` boleh memakai render node —
tanpa ini VAAPI tidak mungkin aktif di dalam container. Cek GID grup device
di host dengan `stat -c '%g' /dev/dri/renderD128` dan samakan angkanya di
`group_add`. Bila mesin tidak punya `/dev/dri`, hapus blok `devices` (encoder
otomatis fallback CPU, aplikasi tetap normal).

**Kompatibel mundur:** payload lama tanpa `encoderMode` otomatis dianggap
`"auto"`; hasil default di mesin tanpa GPU identik dengan v1.1.1 (libx264).

**Detail teknis:**
- `app/services/ffmpeg_worker.py` — `detect_best_encoder()` (cache +
  test encode), `_build_concat_cmd(..., encoder_mode, vaapi_device)`,
  resolusi & logging encoder di `process_job()`, loop attempt dengan
  fallback CPU per video. Blok argumen libx264 lama dipertahankan persis.
- `app/services/job_manager.py` — meneruskan `payload.encoderMode` →
  `meta["encoderMode"]` (default `"auto"`).
- `app/templates/index.html` — dropdown **Encoder** di Panel 5.
- `app/static/app.js` — kirim `encoderMode` di payload `/api/start`.
- `docker-compose.yml` — `devices: /dev/dri` + `group_add` untuk VAAPI.

---

# Video Matrix Generator — v1.1.1

Perbaikan & tambahan di atas v1.1.

## A. Fix: tombol Stop (dan area progress) tidak bisa diklik

**Masalah:** saat proses generate berjalan, seluruh form dikunci
(`body.locked .wrap { pointer-events: none }`) supaya tidak diubah di tengah
jalan. Tombol Stop berada di luar `#progressWrap`, sehingga ikut terkunci dan
tidak bisa diklik — seperti "terhalang sesuatu".

**Perbaikan:** menambah aturan CSS `body.locked #btnStop { pointer-events: auto }`
sehingga tombol Stop tetap bisa diklik selama proses berjalan (pola yang sama
sudah dipakai untuk `#progressWrap`).
- `app/static/style.css`

## B. Baru: Estimasi Ukuran Output (berapa GB)

Menambah panel **Estimasi Ukuran Output** di Panel 5. Setelah memilih mode dan
menekan HITUNG, klik **"Hitung Estimasi Ukuran"** untuk melihat perkiraan total
ukuran (mis. "6144 video ≈ 122.88 GB") beserta rincian per mode: jumlah output,
durasi per video, dan estimasi ukuran.

**Cara hitung:**
- Durasi 1 video output = (klip per output) × (rata-rata durasi klip di grid,
  diprobe via ffprobe).
- Ukuran 1 video = bitrate × durasi ÷ 8. Bitrate video diasumsikan ~8 Mbps
  (1080×1920 @30fps, CRF 20); audio 192 kbps hanya bila tidak di-mute.
- Total per mode = ukuran 1 video × jumlah output (mengikuti batch limit bila
  diaktifkan).

**Catatan penting:** encoder memakai **CRF (variable bitrate)**, jadi ukuran
nyata tergantung isi video. Estimasi ini dibuat **cenderung sedikit lebih besar**
(aman untuk memperkirakan kebutuhan disk): video sederhana/statis bisa jauh lebih
kecil, video ramai gerakan mendekati angka estimasi.

**Detail teknis:**
- `app/services/calculator.py` — fungsi murni `estimate_output_size()`.
- `app/services/ffmpeg_worker.py` — `probe_duration()` + konstanta
  `EST_VIDEO_BITRATE_BPS` / `EST_AUDIO_BITRATE_BPS`.
- `app/app.py` — endpoint `POST /api/estimate_size` (memprobe durasi grid, lalu
  menghitung).
- `app/static/index.html`, `app/static/app.js`, `app/static/style.css` — panel
  estimasi, tombol, dan render hasil. Estimasi otomatis di-reset bila mode /
  batch / mute diubah, supaya tidak menampilkan angka basi.

---

# Video Matrix Generator — v1.1

Ringkasan perubahan pada versi **v1.1**.

---

## 1. Tombol STOP (baru)

Menambahkan tombol **Stop** di Panel *5. Mode Selection & Generate*, di samping
tombol **Generate**. Tombol ini hanya muncul selama proses generate berjalan,
dan hilang otomatis saat proses selesai / dihentikan.

**Perilaku saat Stop ditekan:**
- Proses render yang **sedang berjalan** dihentikan seketika (proses ffmpeg
  yang aktif dibunuh — berhenti dalam hitungan detik, bukan menunggu video
  saat ini selesai).
- Video yang **sudah selesai TIDAK dihapus** — tetap tersimpan rapi di
  `outputs/<run_tag>/<mode>/...`.
- File video yang **setengah jadi** (yang sedang dirender saat Stop ditekan)
  **dihapus** otomatis, supaya folder output bersih dan tidak ada file rusak
  yang ikut terbawa ke aplikasi Remote HP.
- Status job menjadi `cancelled`; ringkasan berapa video yang selesai tetap
  bisa dilihat di panel Progress.

Ada dialog konfirmasi sebelum benar-benar berhenti, agar tidak terhenti karena
salah klik.

**Cara menghentikan proses yang sedang berjalan dari terminal (Ubuntu):**
Karena beban kerja sebenarnya ada di ffmpeg, hentikan ffmpeg-nya:
```bash
pkill -INT ffmpeg      # hentikan dengan rapi (seperti Ctrl+C)
# jika masih ada yang bandel:
pkill -9 ffmpeg
```
Jika dijalankan via Docker:
```bash
docker compose down
```

**Detail teknis:**
- `app/services/job_manager.py` — flag `cancelRequested` per job + fungsi
  `request_stop(job_id)`.
- `app/services/ffmpeg_worker.py` — ffmpeg dijalankan lewat `Popen` (bukan
  `subprocess.run` yang blocking) sehingga bisa dipantau & dibunuh di tengah
  encode; cek pembatalan sebelum tiap video dan saat proses berjalan; hapus
  file setengah jadi; status akhir `cancelled`.
- `app/app.py` — endpoint baru `POST /api/stop/<job_id>`.
- `app/static/app.js` — tombol Stop, pelacakan job aktif, penanganan status
  `cancelled` di loop polling.

---

## 2. Default folder policy = "Folder isi 24 Video"

Di Panel *5. Mode Selection & Generate*, pilihan **Folder management output**
kini default ke **"Folder isi 24 Video"** (sebelumnya default "Folder isi 4
Video"). Pilihan lain (Semua / 4 / 5 / Manual) tetap tersedia.

- `app/templates/index.html` — atribut `selected` dipindah ke `<option value="24">`.

---

## Keselarasan dengan aplikasi Remote HP

Kedua aplikasi sudah **selaras** pada kontrak yang penting, tidak perlu
perubahan kode untuk kompatibilitas:

- **Struktur output cocok.** VMG menulis ke
  `outputs/<run_tag>/<mode>/<bundle>/video_0001.mp4` dengan subfolder bernama
  angka (`1`, `2`, `3`, …) dan file `video_0001.mp4`, `video_0002.mp4`, …
  Remote HP membaca persis pola ini (subfolder angka + `video_000N.mp4`,
  natural sort).
- **Nilai folder policy sama.** VMG: `all / 4 / 5 / 24 / custom`. Remote HP:
  `4 / 5 / 24 / All / Manual`. "Folder isi 24 Video" di VMG = policy `24` di
  Remote HP.
- **Port tidak bentrok.** VMG di port **5000**, Remote HP di port **5001** —
  bisa jalan bersamaan.
- **Anti-duplikasi (Remote HP v1.1.4) cocok dengan penomoran berulang VMG.**
  VMG membuat nama file yang sama tiap run; Remote HP kini mengunci duplikat
  berdasarkan **(nama file + tanggal batch)**, jadi nama sama boleh diupload
  ulang di tanggal berbeda. Ini justru mendukung alur kerja harian.

**Catatan pemakaian (bukan bug):** saat memilih folder di Remote HP, arahkan ke
folder **mode** yang langsung berisi subfolder angka, mis.
`.../outputs/20260703_120000/horizontal/`, bukan ke folder `run_tag`-nya.
