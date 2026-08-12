"""
services/guard.py — Penjaga anti-duplikasi upload (v1.1.5)

Perubahan penting v1.1.5
------------------------
Sebelumnya (v1.1.4) duplikat dikunci pada (nama file + tanggal batch), sehingga
nama file yang sama TIDAK bisa diupload lagi di hari yang sama — padahal isinya
berbeda. Ini menyusahkan alur kerja nyata.

Kenyataan alur kerja:
- Video dihasilkan Video Mixer dengan penomoran BERULANG
  (video_0001.mp4, video_0002.mp4, ...). Isi selalu berbeda tiap generate.
- Setelah tiap video sukses diupload, file LANGSUNG DIHAPUS dari PC & HP.
  Jadi proteksi anti-duplikasi yang sebenarnya = file fisiknya hilang; scan
  berikutnya tidak akan menemukannya lagi.

Karena itu, mencocokkan "nama file yang pernah diupload" (baik lewat filepath
maupun nama+tanggal) justru SALAH: itu memblokir konten baru yang sah hanya
karena namanya kebetulan sama.

Kebijakan baru:
- Riwayat upload (tabel uploaded_videos) tetap dicatat untuk keperluan CATATAN
  (tanggal berapa upload apa) — TIDAK dipakai lagi sebagai penghalang.
- Semua video yang ada di folder dianggap boleh diupload. Nama sama + hari sama
  + isi beda => BOLEH. Nama sama + hari beda => BOLEH.
- Proteksi terhadap dobel-upload yang tidak disengaja tetap ada di lapisan lain:
    (a) file dihapus otomatis setelah upload (tidak akan ke-scan lagi), dan
    (b) di dalam 1 sesi, alur FIFO menandai tiap video 'done' sehingga tidak
        bisa dikirim dua kali.

Fungsi-fungsi di bawah dipertahankan signature-nya agar kode pemanggil tidak
berubah, namun kini tidak pernah menandai video sebagai duplikat.
"""


def is_uploaded(filename, batch_date=None):
    """
    Dipertahankan untuk kompatibilitas. Selalu mengembalikan "belum diupload"
    karena riwayat tidak lagi dipakai sebagai penghalang (lihat penjelasan modul).

    Return dict { uploaded: False, info: None }
    """
    return {"uploaded": False, "info": None}


def filter_uploadable(videos, batch_date=None):
    """
    Semua video dianggap boleh diupload (tidak ada yang dianggap duplikat).

    Return dict:
    {
      uploadable: [...],   # = semua video apa adanya
      duplicates: [],      # selalu kosong
    }
    """
    return {"uploadable": list(videos or []), "duplicates": []}


def can_upload(filename, batch_date=None):
    """Selalu True — video boleh diupload."""
    return True


def count_uploads_for_account(account_id):
    """Hitung total video yang sudah diupload oleh 1 akun (untuk statistik/riwayat)."""
    from database.db import query
    row = query(
        "SELECT COUNT(*) AS c FROM uploaded_videos WHERE account_id = ?",
        (account_id,),
        one=True,
    )
    return row["c"] if row else 0
