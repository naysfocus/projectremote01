-- ============================================
-- Remote HP — Database Schema (SQLite)
-- ============================================

-- Tabel: devices (HP)
CREATE TABLE IF NOT EXISTS devices (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  name                TEXT NOT NULL,
  serial              TEXT, -- kompatibilitas legacy; runtime tidak lagi bergantung pada kolom ini
  label               TEXT,
  notes               TEXT,
  stable_uid          TEXT, -- identitas HP lokal yang tidak berubah saat transport ADB berubah
  usb_serial          TEXT, -- serial ADB USB, bila pernah diketahui
  wifi_endpoint       TEXT, -- endpoint ADB Wi-Fi (ip:port), terpisah dari identitas HP
  preferred_transport TEXT DEFAULT 'auto', -- auto / wifi / usb
  wifi_auto_reconnect INTEGER DEFAULT 1,
  last_transport      TEXT,
  last_usb_seen_at    DATETIME,
  last_wifi_seen_at   DATETIME,
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabel: accounts (Akun TikTok)
-- v1.46 — AKUN LINTAS-HP: sebuah akun adalah SATU identitas independen dari
-- HP manapun (kunci: username, case-insensitive unik). Akun TIDAK LAGI
-- "dimiliki" oleh satu device_id — akun bisa ditempatkan di banyak HP
-- sekaligus lewat tabel account_placements di bawah. Semua riwayat/sesi/video
-- menempel ke accounts.id yang STABIL, tidak peduli akun sedang/pernah
-- ditempatkan di HP mana saja.
CREATE TABLE IF NOT EXISTS accounts (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  username   TEXT NOT NULL,
  email      TEXT,
  password   TEXT,
  phone      TEXT,
  notes      TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Username unik (case-insensitive) — satu akun = satu identitas di seluruh sistem.
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_username_ci ON accounts(username COLLATE NOCASE);

-- Tabel: account_placements (penghubung many-to-many Akun <-> HP)
-- v1.46: satu akun boleh "ditempatkan" di banyak HP sekaligus (mis. anisa.567
-- ada di HP-1 DAN HP-2), masing-masing penempatan punya slot aplikasi
-- (original/kloning) SENDIRI-SENDIRI per HP — bisa beda antar HP.
-- Menghapus satu placement HANYA melepas akun dari HP itu; akun & seluruh
-- riwayat/sesinya (menempel ke account_id) tetap utuh selama masih ada
-- placement lain, atau bahkan bila sudah tidak ada placement sama sekali
-- (akun "tanpa HP" — riwayat tetap bisa dilihat, tinggal ditempatkan lagi).
CREATE TABLE IF NOT EXISTS account_placements (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  device_id  INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  app_slot   TEXT NOT NULL DEFAULT 'original',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Satu akun hanya boleh punya SATU penempatan per HP (tidak boleh dobel
-- baris utk HP yang sama), tapi boleh beda app_slot antar HP yang berbeda.
CREATE UNIQUE INDEX IF NOT EXISTS idx_placements_account_device ON account_placements(account_id, device_id);

-- Tabel: upload_sessions (Sesi Upload)
CREATE TABLE IF NOT EXISTS upload_sessions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  device_id   INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  folder_path TEXT NOT NULL,
  subfolder   TEXT NOT NULL,
  policy      INTEGER NOT NULL, -- kompatibilitas; sesi baru selalu bernilai 24 sejak v1.41
  batch_date  TEXT,               -- tanggal jadwal / penanda batch (YYYY-MM-DD) — v1.1.4
  status      TEXT DEFAULT 'pending',
  started_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME
);

-- Tabel: uploaded_videos (Video yang sudah diupload)
CREATE TABLE IF NOT EXISTS uploaded_videos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  INTEGER NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
  account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  filename    TEXT NOT NULL,
  filepath    TEXT NOT NULL,
  file_hash   TEXT,
  batch_date  TEXT,               -- tanggal batch (YYYY-MM-DD) — kunci anti-duplikasi v1.1.4
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabel: caption_templates
CREATE TABLE IF NOT EXISTS caption_templates (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  content    TEXT NOT NULL,
  hashtags   TEXT,
  is_active  INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabel: settings
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);



-- v1.50: pairing code Android sekali pakai. Plaintext tidak disimpan.
CREATE TABLE IF NOT EXISTS mobile_pairing_codes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id   INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  code_hash   TEXT NOT NULL UNIQUE,
  code_hint   TEXT NOT NULL,
  expires_at  TEXT NOT NULL,
  used_at     TEXT,
  revoked_at  TEXT,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- v1.50: Android Controller yang sudah dipasangkan ke satu HP.
-- Bearer token hanya disimpan sebagai SHA-256.
CREATE TABLE IF NOT EXISTS mobile_clients (
  id                       INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id                INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  app_device_uuid          TEXT NOT NULL UNIQUE,
  display_name             TEXT NOT NULL DEFAULT 'Remote HP Android',
  token_hash               TEXT UNIQUE,
  token_prefix             TEXT,
  status                   TEXT NOT NULL DEFAULT 'active',
  paired_at                TEXT NOT NULL,
  last_seen_at             TEXT,
  revoked_at               TEXT,
  app_version              TEXT,
  overlay_contract_version TEXT NOT NULL DEFAULT '1.0',
  created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mobile_pairing_device ON mobile_pairing_codes(device_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_mobile_clients_device ON mobile_clients(device_id, status);

-- ============================================
-- Index untuk query yang sering dipakai
-- ============================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_devices_stable_uid ON devices(stable_uid);
CREATE INDEX IF NOT EXISTS idx_devices_usb_serial ON devices(usb_serial);
CREATE INDEX IF NOT EXISTS idx_devices_wifi_endpoint ON devices(wifi_endpoint);
CREATE INDEX IF NOT EXISTS idx_sessions_account   ON upload_sessions(account_id);
CREATE INDEX IF NOT EXISTS idx_videos_session     ON uploaded_videos(session_id);
CREATE INDEX IF NOT EXISTS idx_videos_account     ON uploaded_videos(account_id);
CREATE INDEX IF NOT EXISTS idx_videos_filepath    ON uploaded_videos(filepath);
-- v1.1.4: anti-duplikasi berbasis (nama file + tanggal batch)
CREATE INDEX IF NOT EXISTS idx_videos_name_date   ON uploaded_videos(filename, batch_date);
CREATE INDEX IF NOT EXISTS idx_sessions_batchdate ON upload_sessions(batch_date);
-- v1.46: penempatan akun per HP & slot aplikasi (ganti idx_accounts_device_slot lama)
CREATE INDEX IF NOT EXISTS idx_placements_device_slot ON account_placements(device_id, app_slot);
