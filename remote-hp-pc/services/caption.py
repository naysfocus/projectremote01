"""
services/caption.py — Random caption generator (v1.1.8)

Perubahan v1.1.8:
- Hashtag DIPAKSA maksimal 3 (MAX_HASHTAGS) di generate_caption(), apa pun
  jumlah yang tersimpan di template — jadi berlaku juga untuk template lama.
- Ditambah flag_risky_caption(): deteksi kata/frasa "berisiko" (over-claim,
  klaim hasil, ajakan checkout langsung) untuk memPERINGATKAN user saat
  menyimpan template baru (bukan memblokir — keputusan tetap di user).

Gaya template default (di database/db.py) juga diubah total: tidak lagi memuji
produk / menyuruh checkout, melainkan berputar pada perilaku & psikologi
konsumen yang umum.

Dipakai oleh upload workflow & halaman pengaturan.
"""
import random
import re

from database.db import query

# Batas keras jumlah hashtag pada caption yang dihasilkan.
MAX_HASHTAGS = 3

# Sinonim inline yang diganti acak langsung di teks (tanpa perlu slot).
# Sengaja NETRAL — tidak menambah klaim kualitas/hasil pada produk.
INLINE_SYNONYMS = {
    "biasanya": ["biasanya", "seringnya", "kebanyakan"],
    "penasaran": ["penasaran", "kepo", "pengin tahu"],
    "mikir": ["mikir", "nimbang", "muter otak"],
    "kadang": ["kadang", "sesekali", "ada kalanya"],
}

# ── Daftar kata/frasa "berisiko" untuk validasi template (task 3c) ──
# Dikelompokkan agar pesan peringatannya bisa menjelaskan JENIS risikonya.
RISKY_PATTERNS = {
    "klaim kualitas / over-claim": [
        "bagus banget", "sangat bagus", "berkualitas", "kualitas terbaik",
        "worth it", "recommended", "wajib punya", "wajib beli", "wajib coba",
        "terbaik", "paling bagus", "no.1", "nomor 1", "juara", "ori 100",
        "dijamin", "garansi hasil", "pasti puas", "bikin nagih", "auto repeat",
    ],
    "klaim hasil": [
        "hasilnya memuaskan", "langsung berhasil", "terbukti", "ampuh",
        "instan", "seketika", "permanen", "menyembuhkan", "menghilangkan",
        "memutihkan", "melangsingkan", "100% berhasil", "pasti berhasil",
    ],
    "ajakan beli / checkout langsung": [
        "checkout", "check out", "co sekarang", "beli sekarang", "order sekarang",
        "buruan beli", "buruan order", "keranjang kuning", "klik keranjang",
        "langsung beli", "langsung order", "jangan sampai kehabisan", "stok terbatas",
        "diskon", "promo", "flash sale", "harga termurah", "termurah",
    ],
}

# Frasa yang boleh mengandung substring berisiko tapi sebetulnya aman
# (whitelist kecil untuk mengurangi false-positive).
_RISKY_WHITELIST = [
    "promosi berlebihan",  # justru sedang membahas TENTANG promosi
]


def _get_active_templates():
    return query("SELECT * FROM caption_templates WHERE is_active = 1 ORDER BY id")


def _apply_inline_synonyms(text):
    """Ganti beberapa frasa dengan sinonim acak (case-insensitive, sekali per frasa)."""
    result = text
    for phrase, options in INLINE_SYNONYMS.items():
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(result):
            choice = random.choice(options)
            result = pattern.sub(choice, result, count=1)
    return result


def _shuffle_hashtags(hashtags_str, limit=MAX_HASHTAGS):
    """
    Acak urutan hashtag lalu POTONG jadi maksimal `limit` buah.

    Pemotongan dilakukan setelah pengacakan supaya hashtag yang tampil ikut
    bervariasi antar-generate, bukan selalu 3 yang pertama. Token tanpa '#'
    di depan diberi '#'. Duplikat (case-insensitive) dibuang.
    """
    if not hashtags_str:
        return ""
    raw = [t.strip() for t in hashtags_str.split() if t.strip()]
    # normalisasi: pastikan diawali '#', buang duplikat
    seen = set()
    tags = []
    for t in raw:
        tag = t if t.startswith("#") else ("#" + t.lstrip("#"))
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
    if not tags:
        return ""
    random.shuffle(tags)
    tags = tags[: max(0, int(limit))]
    return " ".join(tags)


def generate_caption(template_id=None):
    """
    Generate 1 caption.
    Jika template_id diberikan, pakai itu; jika tidak, pilih acak dari yang aktif.
    Hashtag hasil akhir DIBATASI maksimal MAX_HASHTAGS (3).

    Return dict: { content, hashtags, full, template_id, empty }
    """
    templates = _get_active_templates()
    if not templates:
        return {
            "content": "",
            "hashtags": "",
            "full": "",
            "template_id": None,
            "empty": True,
        }

    if template_id:
        tpl = next((t for t in templates if t["id"] == template_id), None)
        if not tpl:
            tpl = random.choice(templates)
    else:
        tpl = random.choice(templates)

    content = _apply_inline_synonyms(tpl["content"] or "")
    hashtags = _shuffle_hashtags(tpl["hashtags"] or "", limit=MAX_HASHTAGS)
    full = content
    if hashtags:
        full = f"{content}\n\n{hashtags}"

    return {
        "content": content,
        "hashtags": hashtags,
        "full": full,
        "template_id": tpl["id"],
        "empty": False,
    }


def flag_risky_caption(text):
    """
    Periksa apakah teks caption (dan/atau hashtag) mengandung kata/frasa
    berisiko: over-claim, klaim hasil, atau ajakan checkout langsung.

    TIDAK memblokir apa pun — hanya mengembalikan temuan agar UI bisa
    menampilkan PERINGATAN; keputusan akhir tetap di tangan user.

    Return dict:
      {
        "risky": bool,
        "matches": [ {"phrase": str, "category": str}, ... ],
        "categories": [ "kategori terdeteksi", ... ],
      }
    """
    matches = []
    if text:
        low = " " + text.lower() + " "
        # buang bagian yang di-whitelist supaya tidak memicu false-positive
        for w in _RISKY_WHITELIST:
            low = low.replace(w, " ")
        for category, phrases in RISKY_PATTERNS.items():
            for phrase in phrases:
                if phrase in low:
                    matches.append({"phrase": phrase, "category": category})

    # de-duplikasi frasa (jaga urutan)
    seen = set()
    uniq = []
    for m in matches:
        if m["phrase"] in seen:
            continue
        seen.add(m["phrase"])
        uniq.append(m)

    categories = []
    for m in uniq:
        if m["category"] not in categories:
            categories.append(m["category"])

    return {"risky": bool(uniq), "matches": uniq, "categories": categories}


def list_templates():
    """Semua template (aktif & nonaktif) untuk halaman pengaturan."""
    return query("SELECT * FROM caption_templates ORDER BY id DESC")


# ════════════════════════════════════════
# PARSER FILE CAPTION (unggah .md / .txt)
# ════════════════════════════════════════
def parse_caption_file(text):
    """
    Ubah isi file markdown/txt menjadi daftar caption terstruktur.

    ATURAN FORMAT (sengaja sederhana & manusiawi):
    - Tiap caption dipisah oleh BARIS KOSONG (satu blok = satu caption),
      persis seperti menulis paragraf terpisah.
    - Pemisah markdown '---' (garis horizontal) juga dianggap batas antar
      caption, jadi boleh dipakai kalau mau lebih eksplisit.
    - Di dalam satu blok, baris yang DIAWALI '#'/'＃' dianggap baris HASHTAG
      (bukan bagian isi caption). Beberapa baris hashtag digabung. Ini juga
      otomatis membedakan hashtag dari heading markdown — tapi untuk aman,
      heading markdown umum ('# Judul', '## Sub') yang jelas berupa judul
      dokumen (bukan kumpulan tag) diabaikan bila TIDAK diikuti kata berawalan
      '#' lain — lihat _looks_like_hashtag_line().
    - Bullet list markdown ('- ', '* ', '1. ') di awal baris dibersihkan,
      supaya kalau user menulis caption sebagai daftar berpoin tetap kebaca
      rapi.

    Return dict:
      {
        "captions": [ {"content": str, "hashtags": str}, ... ],
        "count": int,
        "skipped_empty": int,   # blok yang kosong/tak berisi teks, dilewati
      }
    """
    if not text:
        return {"captions": [], "count": 0, "skipped_empty": 0}

    # Normalisasi newline
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Pecah jadi blok: pisah oleh baris kosong ATAU garis '---' / '***' / '___'
    blocks = []
    current = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        is_hr = stripped in ("---", "***", "___") or (
            len(stripped) >= 3 and set(stripped) <= {"-"} 
        )
        if stripped == "" or is_hr:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)

    captions = []
    skipped_empty = 0
    for block in blocks:
        # Lewati blok yang kemungkinan besar JUDUL DOKUMEN: hanya 1 baris & baris
        # itu berupa heading markdown ('# ...', '## ...'). Caption asli hampir
        # tidak pernah ditulis sebagai heading 1-baris tunggal, jadi ini aman
        # untuk membuang judul semacam "# Kumpulan Caption" tanpa menyentuh isi.
        non_empty_lines = [ln for ln in block if ln.strip()]
        if len(non_empty_lines) == 1 and re.match(r"^#{1,6}\s+\S", non_empty_lines[0].strip()):
            skipped_empty += 1
            continue

        content_lines = []
        hashtag_tokens = []
        for line in block:
            stripped = line.strip()
            if _looks_like_hashtag_line(stripped):
                hashtag_tokens.extend(
                    t for t in stripped.split() if t.startswith("#") or t.startswith("＃")
                )
            else:
                content_lines.append(_clean_content_line(stripped))

        content = " ".join(cl for cl in content_lines if cl).strip()
        # normalkan ＃ -> # dan buang duplikat sambil jaga urutan
        seen = set()
        norm_tags = []
        for t in hashtag_tokens:
            tag = "#" + t.lstrip("#＃")
            key = tag.lower()
            if tag == "#" or key in seen:
                continue
            seen.add(key)
            norm_tags.append(tag)
        hashtags = " ".join(norm_tags)

        if not content and not hashtags:
            skipped_empty += 1
            continue
        # blok yang hanya berisi hashtag tanpa teks juga dilewati (tak bermakna sbg caption)
        if not content:
            skipped_empty += 1
            continue

        captions.append({"content": content, "hashtags": hashtags})

    return {"captions": captions, "count": len(captions), "skipped_empty": skipped_empty}


def _looks_like_hashtag_line(line):
    """
    True jika baris ini lebih tepat dianggap baris HASHTAG, bukan isi caption.

    Kriteria: setelah dipecah spasi, MAYORITAS token diawali '#'/'＃' dan ada
    minimal 1 token hashtag. Ini membedakan '#fyp #tips #belanja' (baris tag)
    dari heading markdown '# Judul Panjang Dokumen Ini' (yang cuma 1 '#' di
    depan lalu diikuti kata-kata biasa — mayoritas token BUKAN hashtag).
    """
    if not line:
        return False
    tokens = line.split()
    if not tokens:
        return False
    hash_tokens = [t for t in tokens if t.startswith("#") or t.startswith("＃")]
    if not hash_tokens:
        return False
    # mayoritas token adalah hashtag
    return len(hash_tokens) >= max(1, (len(tokens) + 1) // 2)


def _clean_content_line(line):
    """Bersihkan penanda markdown umum di AWAL baris (bullet/heading/quote)."""
    # heading markdown: '#', '##', ... (hanya jika diikuti spasi lalu teks)
    line = re.sub(r"^#{1,6}\s+", "", line)
    # bullet list: '- ', '* ', '+ '
    line = re.sub(r"^[-*+]\s+", "", line)
    # numbered list: '1. ', '2) '
    line = re.sub(r"^\d+[.)]\s+", "", line)
    # blockquote: '> '
    line = re.sub(r"^>\s+", "", line)
    return line.strip()
