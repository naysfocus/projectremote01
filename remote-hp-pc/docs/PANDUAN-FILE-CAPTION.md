# Panduan Format File Caption

File ini menjelaskan cara membuat file caption yang bisa diunggah lewat
menu **Pengaturan → Template Caption → "📄 Unggah File"** di aplikasi Remote HP.
Lihat `contoh-caption.md` untuk contoh siap pakai.

## Aturan Format (sederhana)

1. **Satu caption = satu blok**, dipisahkan oleh **satu baris kosong**.
2. Baris yang **diawali `#`** otomatis dianggap **hashtag** (taruh di baris
   terpisah tepat di bawah teks caption-nya). Boleh beberapa hashtag dalam
   satu baris, dipisah spasi. Hashtag duplikat otomatis dibuang.
3. Caption **boleh tanpa hashtag** sama sekali — cukup tulis teksnya saja.
4. Format **markdown didukung**: garis pemisah `---`, bullet `- `, penomoran
   `1. `, dan kutipan `> ` di awal baris akan dibersihkan otomatis. Baris
   **judul** markdown yang berdiri sendiri (`# Judul`) akan **dilewati**.
5. Ukuran file maksimal **1 MB**, maksimal **1000 caption** per file.

## Contoh Isi File

```
Kadang sebelum belanja tuh aku scroll dulu lama-lama, baca-baca
#fyp #belanjaonline #tips

Menurut kalian, lebih sering belanja karena butuh, atau kebetulan lihat pas scroll?
#fyp #tanya

Caption tanpa hashtag juga boleh
```

## Mode Unggah

- **Tambahkan** (append): caption dari file ditambahkan ke daftar yang sudah ada.
- **Ganti semua** (replace): semua caption lama dihapus, diganti isi file ini.

## Tips Isi Caption

Fokus ke **perilaku & psikologi konsumen** (kebiasaan scroll, cara menimbang
keputusan, mood saat belanja), **bukan** memuji produk atau mengajak beli
langsung. Aplikasi akan memberi **peringatan** (bukan blokir) bila mendeteksi
frasa yang berpotensi over-claim seperti "dijamin", "wajib beli", "checkout
sekarang", "diskon", dsb.
