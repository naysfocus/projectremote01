# 🚀 CARA SETUP & MENJALANKAN — Remote HP

Panduan ini ditulis untuk pemula. Ikuti langkahnya sesuai sistem operasi
komputer Anda. **Setup hanya dilakukan SATU KALI** di setiap komputer baru.

---

## 📋 Konsep singkat (penting tapi mudah)

Aplikasi ini berjalan langsung di komputer (bukan di dalam Docker). Karena itu,
komputer perlu punya beberapa "alat" dulu sebelum aplikasi bisa jalan. Istilah
yang Anda dengar — **environment / requirement / dependency** — artinya semua
"alat" itu:

| Istilah | Maksudnya |
|---|---|
| **winget (Windows Package Manager)** | Alat bawaan Windows untuk install program lewat perintah — dipakai script setup untuk memasang semua di bawah ini secara otomatis (Windows saja) |
| **Python** | "Mesin" yang menjalankan aplikasi ini |
| **Virtual environment (.venv)** | Kotak terpisah berisi library aplikasi, supaya tidak bentrok dengan program lain |
| **Dependency / requirement** | Library yang dibutuhkan (di sini: Flask) |
| **ADB** | Jembatan agar komputer bisa kirim file ke HP lewat kabel USB |
| **scrcpy** | Alat untuk menampilkan (mirror) layar HP di komputer |
| **xdotool** | Alat Ubuntu untuk memfokuskan scrcpy dan mengirim `Ctrl+V` pada fitur Tempel ke HP |

**Kabar baik:** Anda tidak perlu menginstall semua itu manual. Cukup jalankan
**1 file setup**, dan semuanya akan dicoba disiapkan otomatis. ✅

---

## 🪟 WINDOWS

### Setup (satu kali saja)

1. Ekstrak file ZIP ini ke folder mana saja (mis. `C:\RemoteHP`).
2. Buka folder itu.
3. **Klik 2x** file `setup-windows.bat`.
4. Tunggu sampai muncul tulisan **"SETUP SELESAI!"**.

Kalau Python belum ada, script akan memasangnya otomatis. Setelah itu ia minta
Anda **menutup jendela lalu klik 2x `setup-windows.bat` lagi** — ini normal,
lakukan saja.

> 💡 Kalau `winget` (Windows Package Manager) belum ada di komputer Anda,
> script akan **mencoba memasangnya sendiri terlebih dahulu** (langkah paling
> awal) — tanpa perlu Anda membuka Microsoft Store. Kalau berhasil, semua
> langkah setelahnya (Python, ADB, scrcpy) bisa ikut terpasang otomatis
> di jalan yang sama. Kalau gagal (jarang, biasanya di PC dengan kebijakan
> keamanan ketat), script akan tetap kasih instruksi manual yang jelas.

> 💡 Kalau Windows menampilkan peringatan biru "Windows protected your PC",
> klik **More info → Run anyway**. (Ini muncul karena file `.bat` buatan
> sendiri, bukan dari toko aplikasi — aman.)

### Menjalankan (setiap kali mau pakai)

- **Klik 2x** file `jalankan-windows.bat`.
- Browser akan terbuka otomatis ke **http://localhost:5001**.
- Selama dipakai, **biarkan jendela hitam tetap terbuka**.
- Untuk berhenti: tutup jendela hitam itu.

---

## 🐧 UBUNTU / LINUX

### Setup (satu kali saja)

1. Ekstrak file ZIP ini ke folder mana saja (mis. `~/RemoteHP`).
2. Buka **Terminal** di folder itu. (Di file manager: klik kanan di area
   kosong → **Open in Terminal**.)
3. Salin-tempel perintah berikut, lalu tekan Enter:

```bash
chmod +x setup-ubuntu.sh jalankan-ubuntu.sh && ./setup-ubuntu.sh
```

4. Saat diminta password, ketik password login Anda (untuk memasang Python &
   ADB). Tunggu sampai muncul **"SETUP SELESAI!"**.

> 💡 Alternatif tanpa Terminal: klik 2x `setup-ubuntu.sh`, lalu pilih
> **"Run in Terminal"**. Kalau pilihan itu tidak muncul, pakai cara Terminal
> di atas (lebih pasti).

### Menjalankan (setiap kali mau pakai)

Salin-tempel perintah berikut di Terminal pada folder ini:

```bash
./jalankan-ubuntu.sh
```

(atau klik 2x `jalankan-ubuntu.sh` → **Run in Terminal**)

- Browser akan terbuka otomatis ke **http://localhost:5001**.
- Selama dipakai, **biarkan Terminal tetap terbuka**.
- Untuk berhenti: tekan **Ctrl + C** di Terminal.

---

## 📱 Menyiapkan HP (berlaku di Windows & Ubuntu)

Agar aplikasi bisa mengirim video ke HP:

1. Di HP: aktifkan **Opsi Pengembang** (ketuk *Nomor Build / Build Number*
   7x di Pengaturan → Tentang Ponsel).
2. Aktifkan **USB Debugging** di Opsi Pengembang.
3. Sambungkan HP ke komputer dengan kabel USB.
4. Di HP akan muncul popup **"Izinkan USB Debugging?"** → centang
   *Selalu izinkan* → **OK**.
5. Di aplikasi, klik tombol **refresh status HP** untuk memastikan HP terdeteksi
   (status jadi hijau/online).

### 🖥️ Mirror layar HP (scrcpy)

Aplikasi punya tombol **🖥️ Mirror** di tiap kartu HP (di sidebar). Klik tombol
itu untuk menampilkan layar HP di komputer — Anda bisa kontrol HP pakai
mouse/keyboard tanpa buka aplikasi lain.

- Jendela mirror muncul **terpisah** dari browser (ini wajar — bisa Anda geser
  ke monitor/area lain sambil tetap pakai aplikasi).
- scrcpy sudah otomatis diinstall oleh script setup. Kalau belum terdeteksi,
  isi lokasinya di **Pengaturan → Path scrcpy**.
- HP harus **online** dulu (status hijau) sebelum bisa di-mirror.

### 📱 Tempel caption ke HP

Setelah video terkirim, sentuh/klik kolom caption TikTok sampai aktif, lalu klik
**Tempel ke HP** pada Panel Caption. Aplikasi menyalin caption, memfokuskan
jendela scrcpy, dan mengirim `Ctrl+V`. Tombol **Copy Semua** tetap tersedia
sebagai cara manual bila auto-paste gagal. Pada Ubuntu, `setup-ubuntu.sh`
otomatis memasang `xdotool` untuk fitur ini.

**Mode Mirror (Pengaturan → Path Sistem)** — atur perilaku jendela mirror:
- **Anti-sleep — HP tidak tidur (default)**: HP tidak akan tidur selama jendela
  mirror terbuka, jadi mouse & keyboard tetap responsif walau lama tidak
  disentuh. (Pakai `--stay-awake`.)
- **Anti-sleep + Matikan layar HP (hemat listrik)**: selain anti-sleep, layar
  fisik HP dimatikan supaya hemat listrik — mirror di komputer tetap jalan
  normal. (Pakai `--stay-awake --turn-screen-off`.)

---

## ❓ Masalah Umum

**"No module named pip" saat setup (Ubuntu)**
→ Biasanya karena ada folder `.venv` lama yang rusak. Versi setup ini sudah
mendeteksi & memperbaikinya otomatis. Kalau masih terjadi, hapus folder `.venv`
lalu jalankan setup lagi:

```bash
rm -rf .venv && ./setup-ubuntu.sh
```

**"Python tidak dikenali" / setup minta dijalankan 2x (Windows)**
→ Normal saat Python baru diinstall. Tutup jendela, klik 2x `setup-windows.bat`
lagi.

**Browser tidak terbuka otomatis**
→ Buka browser manual, ketik alamat: `http://localhost:5001`

**HP tidak terdeteksi / status abu-abu**
→ Pastikan USB Debugging aktif & popup izin di HP sudah di-OK. Coba cabut-colok
kabel. Kalau ADB tidak ketemu, isi lokasi ADB lewat menu **Pengaturan** di
aplikasi.

**Mau pindah ke komputer lain**
→ Cukup salin seluruh folder ini, lalu jalankan setup (`setup-windows.bat`
atau `./setup-ubuntu.sh`) sekali di komputer baru itu.

**Port 5001 sudah dipakai**
→ Aplikasi memang memakai port 5001 (port 5000 dipakai Video Mixer).
Pastikan tidak ada instance Remote HP lain yang sedang berjalan.

---

## 💾 Catatan Data

- Semua data (HP, akun, riwayat) tersimpan di file `remote_hp.db` yang dibuat
  otomatis di folder ini saat aplikasi pertama dijalankan.
- Untuk pindah komputer **berikut datanya**, salin juga file `remote_hp.db`.
- Folder `.venv` tidak perlu disalin — ia dibuat ulang otomatis oleh setup
  di komputer baru.

---

*Untuk detail teknis & struktur project, lihat `README.md`.*
