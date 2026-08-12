"""
services/scheduler.py — Random time generator (Time Randomizer)

Aturan jadwal Remote HP v1.41:
- Sesi baru selalu 24 post dengan slot jam 00 sampai 23.
- Menit hasil generator selalu acak mulai 01 sampai batas yang dipilih.
- Batas menit aman adalah 01..15. Nilai setting di luar rentang itu
  dinormalisasi otomatis agar jadwal tidak menghasilkan MM yang aneh.
- Generator lama tetap tersedia untuk sesi/API sebelum v1.41.

Contoh sesi baru (batas 15 menit):
  Post 1: 00:07   (slot 00:00 → MM acak 01–15)
  Post 2: 01:13   (slot 01:00 → MM acak 01–15)
  Post 3: 02:04   (slot 02:00 → MM acak 01–15)
"""
import random
from datetime import date, datetime


MIN_RANDOM_MINUTE = 1
MAX_RANDOM_MINUTE = 15
DEFAULT_RANDOM_MINUTE = 15


# ── Tanggal batch / jadwal (v1.1.4) ──
def valid_batch_date(s):
    """
    Validasi & normalisasi tanggal batch.

    Terima string 'YYYY-MM-DD'. Return string ternormalisasi (YYYY-MM-DD)
    bila valid, atau None bila tidak valid/kosong. Ini memastikan hanya
    tanggal kalender yang benar (mis. 2026-02-30 ditolak) yang tersimpan.
    """
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return d.isoformat()
    except (ValueError, TypeError):
        return None


def today_str():
    """Tanggal hari ini (lokal) sebagai 'YYYY-MM-DD'."""
    return date.today().isoformat()


def _parse_time(t):
    """Parse 'HH:MM' → (hour, minute). Return None jika invalid."""
    t = (t or "").strip()
    if not t or ":" not in t:
        return None
    try:
        parts = t.split(":")
        if len(parts) != 2:
            return None
        h = int(parts[0])
        m = int(parts[1])
        if 0 <= h < 24 and 0 <= m < 60:
            return (h, m)
    except (ValueError, IndexError):
        return None
    return None


def _format_time(h, m):
    """(hour, minute) → 'HH:MM' dengan wrap-around 24 jam."""
    h = h % 24
    return f"{h:02d}:{m:02d}"


def normalize_random_range(value, default=DEFAULT_RANDOM_MINUTE):
    """
    Normalisasi batas menit acak ke 1..15.

    Setting lama mungkin berisi 0, 20, 30, teks kosong, atau nilai rusak.
    Semua nilai tersebut dipulihkan secara deterministik agar komponen MM
    jadwal tidak pernah keluar dari 01..15.
    """
    try:
        result = int(value)
    except (ValueError, TypeError):
        result = int(default)
    return max(MIN_RANDOM_MINUTE, min(MAX_RANDOM_MINUTE, result))


def normalize_posting_hours(posting_hours):
    """
    Validasi setting jam legacy dan ubah menjadi slot jam HH:00.

    Menit pada input lama (mis. 09:30) sengaja dinormalisasi ke 09:00 karena
    komponen MM adalah tanggung jawab randomizer 01..15. Urutan dipertahankan
    dan slot jam duplikat dibuang.

    Return list string, mis. ['09:00', '12:00', '15:00'].
    """
    if isinstance(posting_hours, str):
        posting_hours = posting_hours.split(",")
    elif posting_hours is None:
        posting_hours = []

    normalized = []
    seen_hours = set()
    for raw in posting_hours:
        parsed = _parse_time(str(raw))
        if not parsed:
            continue
        hour = parsed[0]
        if hour in seen_hours:
            continue
        seen_hours.add(hour)
        normalized.append(_format_time(hour, 0))
    return normalized


def _randomize_one(h, _m, range_minutes):
    """
    Buat satu waktu pada slot jam ``h`` dengan MM acak 01..batas.

    Parameter menit dasar diabaikan dengan sengaja. Ini mencegah dua sumber
    aturan saling bertumpuk, misalnya setting lama 09:30 ditambah offset 15
    yang dahulu bisa menghasilkan 09:45.
    """
    max_minute = normalize_random_range(range_minutes)
    minute = random.randint(MIN_RANDOM_MINUTE, max_minute)
    return _format_time(h, minute)


def generate_schedule(posting_hours, range_minutes=DEFAULT_RANDOM_MINUTE, count=None):
    """
    Generate jadwal acak kompatibilitas lama.

    posting_hours : list/string 'HH:MM' — hanya komponen HH yang dipakai
    range_minutes : batas atas MM acak, dinormalisasi ke 1..15
    count         : jumlah jadwal yang diinginkan (1 video = 1 post)
                    - count <= jumlah slot default -> ambil slot pertamanya
                    - count  > jumlah slot default -> sebar slot jam merata
                      sepanjang 24 jam

    Return list of dict: [{ index, label, time, base }]
    """
    normalized_hours = normalize_posting_hours(posting_hours)
    if not normalized_hours:
        normalized_hours = ["09:00", "12:00", "15:00", "18:00", "21:00"]

    parsed = [_parse_time(t) for t in normalized_hours]
    parsed = [p for p in parsed if p]
    range_minutes = normalize_random_range(range_minutes)

    try:
        n = int(count) if count is not None else len(parsed)
    except (ValueError, TypeError):
        n = len(parsed)
    if n <= 0:
        n = len(parsed)

    # Jam dasar mengikuti jumlah post:
    #  - sedikit (<= daftar default) -> pakai slot jam default
    #  - banyak                     -> sebar slot HH:00 merata 24 jam
    base_list = _base_hours(parsed, n)

    schedule = []
    for i, (base_h, base_m) in enumerate(base_list):
        time_str = _randomize_one(base_h, base_m, range_minutes)
        schedule.append(
            {
                "index": i + 1,
                "label": f"Post {i + 1}",
                "time": time_str,
                "base": _format_time(base_h, 0),
            }
        )
    return schedule


def generate_fixed_session_schedule(range_minutes=DEFAULT_RANDOM_MINUTE):
    """Generate jadwal baku untuk satu sesi baru berisi 24 post.

    Slot jam ditetapkan server menjadi 00:00 sampai 23:00. Pengaturan hanya
    menentukan batas komponen menit acak (01..15). Ini memisahkan aturan jumlah
    post dari preferensi UI dan menjadi dasar yang konsisten untuk web maupun
    Android client.
    """
    range_minutes = normalize_random_range(range_minutes)
    schedule = []
    for i, (base_h, base_m) in enumerate(_even_spread(24)):
        schedule.append(
            {
                "index": i + 1,
                "label": f"Post {i + 1}",
                "time": _randomize_one(base_h, base_m, range_minutes),
                "base": _format_time(base_h, 0),
            }
        )
    return schedule


def valid_ranges():
    """Pilihan batas menit acak yang aman untuk UI."""
    return [5, 10, 15]


def _even_spread(n):
    """
    Sebar ``n`` slot JAM sepanjang 24 jam, semuanya pada HH:00.

    Implementasi lama menyebar berdasarkan total menit. Untuk jumlah seperti
    14, hasil dasarnya bisa 01:43, 03:26, dst.; setelah ditambah offset acak,
    komponen MM terlihat tidak konsisten. v1.40 membulatkan penyebaran ke jam
    terdekat agar randomizer menjadi satu-satunya pembuat komponen MM.

      n = 24 -> 00:00, 01:00, 02:00, ... 23:00
      n = 12 -> 00:00, 02:00, 04:00, ... 22:00
      n = 14 -> slot jam tersebar merata, seluruh base tetap HH:00

    Untuk n > 24, beberapa jam akan berulang karena hanya ada 24 slot jam.
    """
    if n <= 0:
        return []
    out = []
    for i in range(n):
        hour = int(round(i * 24 / n)) % 24
        out.append((hour, 0))
    return out


def _base_hours(parsed, n):
    """
    Tentukan daftar slot jam sepanjang n.

    - n <= jumlah jam default -> ambil n slot pertama dari default.
    - n > jumlah jam default  -> sebar slot HH:00 merata sepanjang 24 jam.
    """
    if n <= len(parsed):
        return [(h, 0) for h, _m in parsed[:n]]
    return _even_spread(n)
