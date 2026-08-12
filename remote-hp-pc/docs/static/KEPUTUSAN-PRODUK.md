# Keputusan Produk yang Disepakati

Dokumen ini mencatat keputusan yang menjadi batas desain, bukan sekadar detail implementasi versi tertentu.

## Perangkat dan operator

- Aplikasi Android dipasang pada HP yang memang sedang dioperasikan.
- Satu instalasi Android terikat ke satu record perangkat server.
- Operator tidak memilih HP dan tidak login dengan username/password setiap kali membuka aplikasi.
- Pairing perangkat dilakukan satu kali saat instalasi atau setelah pairing dicabut.
- ADB serial akan menjadi kolom wajib pada tahap migrasi perangkat berikutnya.

## Sesi upload

- Satu sesi baru selalu berisi **24 post**.
- Pilihan policy `4`, `5`, `All`, dan `Manual` tidak digunakan lagi.
- Server adalah sumber kebenaran jumlah post; nilai jumlah dari client tidak dipercaya.
- Sesi aktif lama dari versi sebelum v1.41 tetap dapat dilanjutkan.

## Jadwal

- Sesi baru memiliki 24 slot jam: `00` sampai `23`.
- Komponen menit dibuat acak dari `01` sampai batas yang dikonfigurasi, maksimum `15`.
- Panel pengaturan jadwal tidak dihapus, tetapi disederhanakan menjadi **Aturan Jadwal 24 Post**.
- Setting `posting_hours` lama dipertahankan sementara untuk kompatibilitas API dan sesi lama, tetapi tidak menjadi sumber jadwal sesi baru 24 post.

## Folder video

- v1.41 masih mempertahankan empat sumber folder lama agar aplikasi tetap dapat digunakan.
- Target berikutnya adalah folder/koleksi dinamis buatan Super Admin.
- Subfolder batch baru harus berisi tepat 24 video.
- Struktur flat lama tetap didukung dengan mengambil 24 video pertama per sesi.

## Penghapusan file

- Setelah post dikonfirmasi selesai, file lokal HP dan file PC diproses sesuai workflow yang sudah ada.
- Desain Android berikutnya harus memakai status penghapusan yang dapat dipulihkan apabila koneksi terputus.
