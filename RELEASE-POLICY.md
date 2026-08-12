# Kebijakan Release Project Remote

Mulai `project-remote-v1.0.zip`, nomor versi distribusi utama berdiri sendiri dari nomor versi masing-masing komponen.

## Format paket

Setiap release selalu dikirim lengkap:

```text
project-remote-v1.X.zip
├── remote-server/
├── remote-hp-pc/
├── video-mixer/
└── remote-hp-android/
```

Dokumen root boleh ditambahkan, tetapi tidak ada ZIP komponen di dalam ZIP utama.

## Aturan kenaikan versi project

- Perubahan satu atau lebih komponen: naikkan project `v1.0 → v1.1 → v1.2`.
- Semua empat folder tetap disertakan meskipun hanya satu komponen berubah.
- Nomor versi komponen hanya dinaikkan bila source komponen tersebut benar-benar berubah.
- Patch bug kecil tetap menghasilkan paket project lengkap berikutnya.
- Release lama tidak ditimpa.

Contoh: apabila hanya Remote HP PC berubah dari 1.50.0 menjadi 1.50.1, distribusinya tetap `project-remote-v1.1.zip` dengan Remote Server, Video Mixer dan Android versi kompatibel ikut disertakan.
