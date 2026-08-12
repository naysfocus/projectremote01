# Video Mixer v1.22.1

> Nama tampilan berubah menjadi **Video Mixer**. ID internal Remote Server tetap `matrix_generator` dan volume aktivasi tetap `video_matrix_client_data`, sehingga aktivasi serta data lama tetap kompatibel.

Aplikasi web lokal untuk membuat **banyak video kombinasi** dari sekumpulan
klip yang disusun dalam grid. Cocok untuk produksi massal variasi video
(mis. konten vertikal 1080×1920). Berjalan di dalam Docker, diakses lewat
browser di `http://localhost:5000`.

Seluruh file video dan proses FFmpeg tetap berjalan **di komputer lokal**. Remote Server hanya menerima aktivasi, heartbeat, status sesi, dan ringkasan jumlah render; file video tidak dikirim ke VPS.

---

## Antarmuka v1.22.1

Setup matriks menempatkan kontrol **Track** lalu **Clip** secara bertumpuk di kiri, sedangkan Estimasi otomatis berada di kanan. Pada mode audio Replace atau Mix, memilih satu atau banyak file langsung memulai upload; tidak ada lagi klik Upload kedua. Status progres dan hasil upload ditampilkan langsung di panel audio.


Panel Storage & pemeliharaan berada pada menu ringkas di header. Popover menampilkan penggunaan `uploads`, `outputs`, `temp`, dan `audio`, lengkap dengan tombol pembersihan terpisah untuk uploads, outputs, dan audio. Tombol **Bersihkan semua** menghapus keempat folder tersebut. Ringkasan matriks, badge Remote Server, serta indikator SIAP/RENDER tidak lagi memenuhi header; validasi Remote Server tetap berjalan melalui banner dan overlay bila akses bermasalah. Kartu Mode kombinasi tetap 2×2 dengan informasi maksimum video sebagai metadata datar tanpa kotak bersarang.

Tampilan Setup diringkas dengan menghapus copy pengantar yang berulang, judul/deskripsi estimasi, footer teknis, pesan kesiapan grid setelah lengkap, dan ringkasan hasil upload massal. Kontrol, angka estimasi, status sel, dan seluruh fungsi render tetap tersedia.

Antarmuka memakai workspace full-width dengan hanya dua tab utama: **Setup** dan **Render**. Pemilihan ukuran matriks dan upload video berada dalam satu tahap Setup. Kalkulasi validitas serta jumlah maksimum kombinasi dijalankan otomatis ketika ukuran grid berubah. Empat angka maksimum tersebut langsung tampil di panel Setup, sebelum video diunggah—tidak ada tombol atau tab Output terpisah.

Grid dibatasi dari **1×1 sampai 10×10**. Matriks memakai seluruh lebar panel dan seluruh baris ditampilkan sekaligus tanpa area scroll internal; tidak ada pilihan Pas, Padat, atau Nyaman. Klik sel untuk melihat detail, klik dua kali atau tombol `+` untuk memilih video. Tombol upload individual kini berbentuk persegi yang lebih besar; tombol upload massal kolom dibuat melebar ke samping dan tombol upload massal baris dibuat memanjang secara vertikal agar lebih mudah dipilih. Lima kartu ringkasan Grid, Total sel, Terisi, Klip/output, dan Kalkulasi tidak lagi ditampilkan pada panel Setup matriks; status pengisian tetap tersedia pada toolbar Matriks upload dan estimasi maksimum tiap mode tetap tersedia pada panel estimasi otomatis. Tab Render terbuka setelah seluruh sel terisi dan kalkulasi otomatis tersedia.

Tab Render memakai dua kolom tetap pada layar lebar. Kolom kiri berurutan **Kualitas output → Folder output → Performa**. Kolom kanan berurutan **Audio & encoder → Jumlah output → Mode kombinasi**. Empat pilihan Mode kombinasi disusun 2 × 2. Setiap kartu hanya menampilkan nama mode, status validitas, dan maksimum video hasil dalam ukuran besar agar mudah diperiksa sebelum Generate.

## Ringkasan cara kerja

1. Tentukan ukuran grid: **Clip** (jumlah kolom) × **Track**
   (jumlah baris).
2. Unggah satu klip untuk setiap sel grid (baris diberi kode A, B, C, …).
3. Pilih **mode kombinasi** yang ingin dibuat:
   - **Acak per Track** — satu track penuh dengan urutan clip bebas.
   - **Acak Lintas Track** — pilih satu track untuk setiap posisi clip, lalu urutan hasil dapat diacak.
   - **Urutan Clip** — pilih satu track untuk setiap posisi dengan urutan clip tetap.
   - **Urutan Clip — Track Unik** — urutan clip tetap dan setiap track hanya boleh digunakan sekali dalam satu output.
4. Aplikasi menghitung jumlah maksimum kombinasi secara otomatis, lalu me-render video.

Semua klip dalam satu output dinormalisasi ke **profil output yang sama**
(resolusi, fps, pixel format `yuv420p`, SAR) agar seragam dan kompatibel di
semua pemutar/platform. Sejak **v1.6** profil ini bisa **dipilih di UI**
(panel *Kualitas output*): resolusi, frame rate, dan mode bitrate
(CRF/kualitas tetap atau bitrate target). **Default = 720×1280 @24fps
kualitas seimbang (CRF 23)** — disetel setara sumber vertikal 720p yang umum
agar tidak ada upscale atau bitrate berlebih (render lebih cepat, file lebih
kecil). Naikkan ke 1080×1920 @30fps hanya bila sumber Anda memang lebih
tinggi.

### Struktur folder hasil

```
outputs/<run_tag>/<mode>/<bundle>/video_0001.mp4
```

`<run_tag>` = waktu render, `<mode>` = horizontal/campuran_horizontal/linear,
`<bundle>` = subfolder bernomor sesuai "Folder output". Penamaan file selalu
`video_0001.mp4`, `video_0002.mp4`, … berurutan dan deterministik.

> Struktur & penamaan ini **tidak berubah** dari versi sebelumnya, sehingga
> aplikasi pendamping (mis. "Remote HP") tetap kompatibel.

---

## Menjalankan

### Windows + Docker Desktop

Cara termudah:

```text
run-windows.bat
```

Atau gunakan Command Prompt pada folder aplikasi:

```bat
docker compose up -d --build
```

Windows Docker Desktop tidak menyediakan `/dev/dri`; v1.22.1 otomatis berjalan dengan encoder CPU sehingga container tetap dapat hidup.

### Linux + Docker

Gunakan helper agar GPU VAAPI dipasang hanya bila `/dev/dri/renderD128` benar-benar tersedia:

```bash
./run.sh
```

Buka `http://localhost:5000`. Pada penggunaan pertama, halaman aktivasi akan muncul. Buat kode **Video Mixer** dari Remote Server, lalu masukkan kode tersebut. Kode berlaku 1 jam.

Menghentikan:

```bash
docker compose down
```

### Aktivasi Remote Server

- Aktivasi hanya dilakukan sekali untuk komputer yang sama.
- Token disimpan otomatis pada volume Docker `video_matrix_client_data`.
- Restart atau rebuild container tidak meminta aktivasi ulang.
- Heartbeat berjalan setiap 5 menit.
- Gangguan internet memakai grace period 3 jam setelah koneksi sukses terakhir.
- Revoke atau konflik sesi langsung memblokir UI dan menghentikan render aktif.

### Menjalankan Linux dengan GPU secara manual

```bash
export RENDER_GID=$(stat -c '%g' /dev/dri/renderD128)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

File utama `docker-compose.yml` sengaja tidak memaksa `/dev/dri`, sehingga perintah standar tetap kompatibel dengan Windows dan komputer tanpa VAAPI.

Prasyarat: **Docker** + **Docker Compose plugin**. Untuk hardware encoding
(GPU) diperlukan `/dev/dri` (umumnya tersedia di Linux dengan GPU AMD/Intel).

---

## Opsi render (tab Render)

### Jumlah output

Pilihan default adalah **Tanpa limit**, sehingga seluruh kombinasi dari mode yang dipilih akan diproses. Angka maksimum per mode dapat diperiksa lebih awal pada panel **Setup matriks**. Untuk grid besar, tinjau estimasi ukuran sebelum Generate atau aktifkan **Dengan limit** dan isi batch size manual.

### Kualitas output (resolusi / fps / bitrate) — baru di v1.6

Panel ini menentukan profil semua video hasil. Ada **Preset cepat** untuk
mengisi semuanya sekaligus, atau atur tiap kontrol secara manual (preset
otomatis berubah ke *Kustom*).

| Kontrol | Pilihan | Default |
|---------|---------|---------|
| **Preset cepat** | *Setara sumber 720p @24fps* · *Seimbang 1080p @30fps* · *Maksimal 1080p @30fps* · *Kustom* | Setara sumber 720p |
| **Resolusi** | 540×960 · 720×1280 · 1080×1920 · 1440×2560 · *Kustom (W×H)* | 720×1280 |
| **Frame rate** | 24 / 25 / 30 / 50 / 60 fps | 24 |
| **Kontrol bitrate** | *Kualitas tetap (CRF)* atau *Bitrate target* | CRF |
| **Kualitas (CRF)** | 18 (tinggi) … 28 (hemat) | 23 |
| **Bitrate video** | angka kbps (saat mode *Bitrate target*) | 2000 kbps |
| **Bitrate audio** | angka kbps (saat suara tidak di-mute) | 128 kbps |

**Kenapa default 720p @24fps?** Sumber vertikal umum sudah 720p, 24fps,
bitrate ~2 Mbps. Versi lama meng-hardcode output ke 1080p @30fps CRF20
sehingga meng-*upscale* dan mem-*boros*-kan waktu render serta ukuran file
(±3× lebih besar dari sumber). Default baru menyamai sumber, jadi tidak ada
pemborosan. Naikkan hanya bila sumber Anda memang lebih tinggi.

- **CRF (kualitas tetap)** — encoder menjaga kualitas, bitrate menyesuaikan
  isi video. Angka lebih kecil = kualitas lebih tinggi (file lebih besar).
  Direkomendasikan.
- **Bitrate target** — encoder membidik bitrate rata-rata tertentu (VBR
  terbatas dengan `maxrate`/`bufsize`). Berguna bila ingin ukuran file lebih
  terprediksi.

> Resolusi/fps/kualitas hanya memengaruhi **isi** file. **Struktur folder dan
> penamaan `video_0001.mp4` tetap sama** — aplikasi pendamping tetap kompatibel.

### Metode render

| Metode | Cara kerja | Kapan dipakai |
|--------|-----------|---------------|
| **Cepat** | Tiap klip unik dinormalisasi **sekali**, lalu tiap output digabung tanpa encode ulang (remux). | Batch besar yang membutuhkan waktu proses lebih singkat. |
| **Klasik** (default) | Tiap output di-encode ulang penuh (perilaku versi lama). | Default paling konservatif dan kompatibel; gunakan Cepat bila ingin optimasi waktu. |

Metode **Cepat** memangkas beban encode dari *(jumlah output × klip per
output)* menjadi *(jumlah klip unik)*. Bila remux sebuah output gagal, aplikasi
otomatis jatuh ke encode penuh untuk output tersebut — jadi hasil tetap aman.

> **v1.7 — perbaikan freeze:** pada versi sebelumnya sebagian output metode
> Cepat bisa *freeze* di posisi acak, terutama bila memakai encoder GPU
> (VAAPI/NVENC). Penyebabnya durasi tiap potongan dihitung dari metadata
> jumlah-frame yang kadang salah/kosong pada encoder hardware, sehingga ada
> celah kecil di sambungan. Sejak v1.7 durasi dihitung dari jumlah frame hasil
> dekode (selalu tepat) dan tiap file perantara dipaksa CFR rapi dari nol —
> sambungan mulus untuk semua encoder. Bila Anda masih menemui freeze, coba
> metode **Klasik** dan laporkan.

### Worker paralel

Jumlah proses render yang berjalan bersamaan (**Auto** / 1–4). **Auto**
menyesuaikan jumlah thread CPU (≈ 1 worker per 6 thread). Nilai lebih tinggi
lebih cepat, tapi lebih berat untuk CPU/RAM.

### Encoder video

| Pilihan | Keterangan |
|---------|-----------|
| **Auto** (rekomendasi) | Pakai GPU bila terdeteksi, otomatis fallback ke CPU. |
| **GPU NVIDIA (NVENC)** | Untuk kartu NVIDIA. |
| **GPU AMD/Intel (VAAPI)** | Untuk iGPU/GPU AMD atau Intel. |
| **CPU (libx264)** | Paling kompatibel, paling berat. |

Encoder yang benar-benar aktif ditampilkan di **chip status** (pojok kanan
atas) dan dicatat di **log render**.

---

## GPU / VAAPI (AMD & Intel)

Agar encode berjalan di iGPU (bukan CPU), container butuh **driver VA-API**.
Versi ini sudah memasangnya di dalam image. Untuk memastikan GPU terbaca:

```bash
docker exec video_mixer_app vainfo
```

Jika muncul daftar profil `VAProfileH264…`, hardware encoding siap. Jika
perintah gagal atau kosong:

- Pastikan host punya `/dev/dri/renderD128`.
- Jalankan lewat `./run.sh` agar `RENDER_GID` benar.
- Bila mesin memang tanpa GPU yang didukung, biarkan encoder di **Auto** —
  aplikasi memakai CPU secara otomatis.

**Catatan panas/CPU:** jika `vainfo` gagal, semua encode jatuh ke CPU dan
penggunaan CPU akan tinggi (ffmpeg bisa memakai banyak core). Mengaktifkan
VAAPI memindahkan beban encode ke iGPU sehingga CPU jauh lebih dingin.

---

## Penyimpanan (Setup → Storage & pemeliharaan)

- **Folder penyimpanan** menampung tiga subfolder: `uploads/` (klip),
  `temp/` (file kerja sementara), `outputs/` (hasil).
- Bisa diganti ke folder/drive lain lewat tombol **Cari folder** → **Terapkan**,
  atau **Reset ke default**.
- Kartu **Penggunaan storage** menampilkan ukuran & jumlah file tiap folder,
  dengan tombol pembersih (uploads / outputs / semua).
- File `temp/` selalu dibersihkan otomatis setelah render selesai, gagal,
  maupun dihentikan.

---

## Menghentikan render

Tombol **Stop** menghentikan proses saat itu. Video yang **sudah selesai tetap
tersimpan**; video yang sedang diproses dibatalkan dan file setengah jadinya
dihapus.

---

## Estimasi ukuran

Di tab Render tersedia **estimasi ukuran output** (total GB perkiraan berdasarkan
durasi klip serta **profil output yang dipilih** — resolusi, fps, dan
CRF/bitrate target). Estimasi mengikuti pilihan di panel *Kualitas output*,
jadi menurunkan resolusi/kualitas langsung terlihat pada perkiraannya. Angka
bersifat perkiraan aman (cenderung sedikit lebih besar) — ukuran nyata
tergantung isi video.

---

## Perawatan Docker (opsional)

```bash
docker system df             # lihat pemakaian disk Docker
docker builder prune         # hapus cache build (image & container aman)
docker system prune          # hapus container stopped, network & image dangling
docker compose down          # hentikan aplikasi
```

Hindari `docker system prune -a --volumes` bila tidak yakin — perintah itu
menghapus banyak data.

---

## Struktur proyek

```
app/
  app.py                  server Flask (endpoint API)
  services/
    calculator.py         hitung kombinasi & rencana job
    ffmpeg_worker.py      mesin render (normalisasi + gabung / encode)
    job_manager.py        state job, progress, riwayat
    storage_config.py     lokasi penyimpanan
  static/                 antarmuka (app.js, style.css)
  templates/index.html    halaman utama
docker/Dockerfile         image (ffmpeg + driver VAAPI)
docker-compose.yml        konfigurasi container
run.sh                    start otomatis (deteksi GPU)
requirements.txt          dependensi Python
CHANGELOG.md              catatan perubahan
```

Detail perubahan versi ada di **CHANGELOG.md**.


## Data yang dikirim ke Remote Server

Hanya metadata operasional: versi aplikasi, fingerprint komputer, status sesi, heartbeat, dan setelah render selesai: mode, jumlah video, durasi proses, serta run tag. Klip sumber dan file output tidak pernah dikirim ke Remote Server.

## Pengaman jumlah output

Default tetap **Tanpa limit**. Tidak ada batas maksimum permanen. Jika jumlah output yang dipilih melebihi **30.000 video**, backend tidak langsung membuat job dan web app menampilkan popup konfirmasi. Pilih **Periksa kembali** untuk memperbaiki konfigurasi atau **Tetap Generate** untuk melanjutkan jumlah yang lebih besar. Konfirmasi otomatis batal jika konfigurasi berubah.

## Waktu Indonesia dan Remote Server

Semua timestamp protokol tetap dikirim dalam UTC agar konsisten, tetapi Video Mixer v1.22.1 juga merekam zona waktu browser, offset UTC, dan waktu lokal saat job dimulai. Remote Server versi berikutnya harus menampilkan waktu menggunakan zona `Asia/Jakarta`; lokasi fisik VPS di Ashburn tidak perlu diubah.
