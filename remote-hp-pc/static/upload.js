/* ============================================
   Remote HP — Upload Workflow (upload.js) v1.42
   Modul wizard upload FIFO
   ============================================ */

const POSTS_PER_SESSION = 24;

const Upload = {
  // state sesi upload aktif
  session: null,        // { session_id, videos, caption, schedule, target_dir, batch_date }
  folderPath: null,
  sourceId: 1,
  sourceRoot: null,
  videoSources: [],
  subfolderName: null,
  subfolderPath: null,
  scanResult: null,
  consoleLines: [],

  // Tombol konfirmasi video aktif setelah caption video aktif disalin manual
  // atau berhasil dikirim lewat tombol Tempel ke HP.
  captionCopiedVideoIndex: null,
  captionPastedVideoIndex: null,
  captionPasteCooldownUntil: 0,

  // Setelah auto-paste berhasil, tombol Selesai di Panel 2 dan Mode Cepat
  // ditahan selama dua detik agar pengguna sempat melihat hasil di HP.
  captionConfirmUnlockAt: 0,
  captionConfirmUnlockVideoIndex: null,
  captionConfirmUnlockTimer: null,

  // State visual Mode Cepat. Dipakai agar tombol baru muncul bertahap dan
  // tombol sebelumnya bergeser ke kiri seperti wizard Next → Next → Finish.
  quickModeRenderedIndex: null,
  quickModeRenderedStage: null,

  // Panel 2 dan Panel 3 diringkas secara default. Pengguna tetap dapat
  // membukanya kapan saja tanpa mengubah state sesi atau isi yang diproses.
  consoleHidden: true,
  captionPreviewHidden: true,

  // Tanggal batch/jadwal (v1.1.4)
  batchDate: null,      // "YYYY-MM-DD" tanggal yang dipilih di Panel 1
  calYear: null,        // tahun yang sedang ditampilkan kalender
  calMonth: null,       // bulan (0-11) yang sedang ditampilkan kalender

  // Penanda tanggal yang SUDAH pernah diupload akun ini (v1.1.21)
  uploadedDates: {},    // { "YYYY-MM-DD": jumlahVideo } untuk akun terpilih
  uploadedDatesAccountId: null,  // account_id yang datanya sedang dimuat (deteksi basi)

  reset() {
    this.session = null;
    this.scanResult = null;
    this.consoleLines = [];
    this.captionCopiedVideoIndex = null;
    this.captionPastedVideoIndex = null;
    this.captionPasteCooldownUntil = 0;
    if (this.captionConfirmUnlockTimer) clearTimeout(this.captionConfirmUnlockTimer);
    this.captionConfirmUnlockAt = 0;
    this.captionConfirmUnlockVideoIndex = null;
    this.captionConfirmUnlockTimer = null;
    this.quickModeRenderedIndex = null;
    this.quickModeRenderedStage = null;
    this.consoleHidden = true;
    this.captionPreviewHidden = true;
    // Bersihkan penanda tanggal upload — akan dimuat ulang untuk akun yang
    // sedang dipilih oleh loadUploadedDates(). (v1.1.21)
    this.uploadedDates = {};
    this.uploadedDatesAccountId = null;
    // Catatan: batchDate sengaja TIDAK direset agar tanggal yang dipilih tetap
    // bertahan saat berpindah antar subfolder/akun dalam alur kerja yang sama.
  },
};

// ════════════════════════════════════════
// Helper tanggal (v1.1.4)
// ════════════════════════════════════════
const HARI_ID = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const BULAN_ID = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];

function pad2(n) {
  return String(n).padStart(2, "0");
}

// "YYYY-MM-DD" dari objek Date (berbasis waktu lokal, bukan UTC)
function toISODate(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

// Tanggal hari ini (lokal) "YYYY-MM-DD"
function todayISO() {
  return toISODate(new Date());
}

// Parse "YYYY-MM-DD" → objek Date lokal (tengah hari untuk hindari geser TZ)
function parseISODate(s) {
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return null;
  return new Date(+m[1], +m[2] - 1, +m[3], 12, 0, 0);
}

// "YYYY-MM-DD" → "Senin, 30 Juni 2026" (untuk tampilan)
function formatBatchDateLong(s) {
  const d = parseISODate(s);
  if (!d) return "—";
  return `${HARI_ID[d.getDay()]}, ${d.getDate()} ${BULAN_ID[d.getMonth()]} ${d.getFullYear()}`;
}

// "YYYY-MM-DD" → "30/06/2026" (ringkas)
function formatBatchDateShort(s) {
  const d = parseISODate(s);
  if (!d) return "—";
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
}

// ════════════════════════════════════════
// ENTRY: render panel upload sesuai konteks
// ════════════════════════════════════════
function renderUploadPanel() {
  const panel = document.getElementById("uploadPanelLeft");
  if (!state.selectedAccount) {
    panel.innerHTML = `<div class="card"><div class="empty-state">
      <div class="emoji">📱</div>
      <div class="title">Belum ada akun dipilih</div>
      <div class="desc">Pilih HP lalu pilih akun dari sidebar kiri untuk memulai sesi upload.</div>
    </div></div>`;
    return;
  }

  // Jika ada sesi aktif → tampilkan workflow
  if (Upload.session) {
    renderWorkflow();
    return;
  }

  // Belum ada sesi → tampilkan step pilih folder
  renderFolderStep();
}

// ════════════════════════════════════════
// STEP: Pilih folder (kebijakan server tetap 24 video)
// ════════════════════════════════════════
function renderFolderStep() {
  const panel = document.getElementById("uploadPanelLeft");
  if (Upload.calYear === null || Upload.calMonth === null) {
    const base = parseISODate(Upload.batchDate) || new Date();
    Upload.calYear = base.getFullYear();
    Upload.calMonth = base.getMonth();
  }

  panel.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title"><div class="step-badge">1</div> Tanggal Jadwal &amp; Batch</div>
        <button class="btn btn-primary btn-sm" id="btnDateToday">📅 Hari Ini</button>
      </div>
      <div class="card-body">
        <div class="date-panel-row">
          <div class="date-picker" id="calPicker"></div>
          <div class="date-side">
            <div class="date-selected-box">
              <div class="date-selected-label">Tanggal Terpilih</div>
              <div class="date-selected-value ${Upload.batchDate ? "" : "empty"}" id="dateSelectedValue">
                ${Upload.batchDate ? escapeHtml(formatBatchDateLong(Upload.batchDate)) : "Belum dipilih"}
              </div>
              ${Upload.batchDate ? `<div class="date-selected-sub" id="dateSelectedSub">${escapeHtml(Upload.batchDate)}</div>` : ""}
            </div>
            <div id="dateUploadedInfo"></div>
            <span class="muted" style="font-size:11.5px;line-height:1.55">
              Tanggal ini dipakai untuk <b>jadwal posting</b> di TikTok Studio <b>dan</b> sebagai <b>penanda batch</b>. Nama file yang sama boleh diupload lagi selama tanggalnya berbeda.
            </span>
            <div style="display:flex;align-items:center;gap:7px;font-size:11.5px;color:var(--muted);margin-top:2px">
              <span style="position:relative;display:inline-block;width:16px;height:16px;border-radius:4px;background:rgba(46,204,113,.12);border:1px solid rgba(46,204,113,.45);flex:none"><span style="position:absolute;right:2px;bottom:2px;width:5px;height:5px;border-radius:50%;background:#2ecc71"></span></span>
              <span>Tanggal bertanda hijau = akun ini <b>sudah pernah upload</b> di tanggal itu. Tetap bisa dipilih untuk upload ulang.</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title"><div class="step-badge">2</div> Pilih Sumber Video</div>
          <div class="card-caption">Pilih salah satu dari empat folder tetap. Lokasi root dikelola dari menu Pengaturan.</div>
        </div>
      </div>
      <div class="card-body">
        <div class="video-source-grid" id="videoSourceGrid">
          <div class="video-source-loading"><span class="spinner"></span> Memuat folder sumber...</div>
        </div>
        <div class="video-source-root" id="videoSourceRoot">
          <span>Root sumber: memuat...</span>
          <button class="btn btn-ghost btn-sm" id="btnOpenVideoSettings">⚙️ Atur di Pengaturan</button>
        </div>
        <div class="video-source-controls">
          <div class="fixed-session-policy" title="Aturan ini ditetapkan oleh server dan berlaku untuk semua sesi baru.">
            <span class="fixed-session-policy-icon">24</span>
            <span><strong>24 video per sesi</strong><small>Kebijakan tunggal dari server</small></span>
          </div>
          <button class="btn btn-primary video-source-scan-btn" id="btnScanFolder" disabled>🔍 Scan Video 1</button>
        </div>
      </div>
    </div>
    <div id="scanResultArea"></div>`;

  renderCalendar();
  loadUploadedDates();
  document.getElementById("btnDateToday").onclick = () => {
    const t = todayISO(); Upload.batchDate = t;
    const d = parseISODate(t); Upload.calYear = d.getFullYear(); Upload.calMonth = d.getMonth();
    updateDateUI(); renderCalendar();
  };

  document.getElementById("btnScanFolder").onclick = scanFolder;
  document.getElementById("btnOpenVideoSettings").onclick = () => switchPage("settings");
  renderVideoSourceGrid();
  loadVideoSources();
  if (Upload.scanResult) renderScanResult(Upload.scanResult);
}

// ════════════════════════════════════════
// KALENDER (Panel 1 — v1.1.4)
// Render kalender bulan Upload.calYear/calMonth dengan jumlah hari benar
// (28/29/30/31), highlight hari ini & tanggal terpilih.
// ════════════════════════════════════════
// Ambil tanggal-tanggal yang SUDAH pernah diupload untuk akun terpilih,
// lalu render ulang kalender agar penanda hijau muncul. (v1.1.21)
async function loadUploadedDates(force = false) {
  const acc = (typeof state !== "undefined" && state.selectedAccount) ? state.selectedAccount : null;
  if (!acc) {
    Upload.uploadedDates = {};
    Upload.uploadedDatesAccountId = null;
    return;
  }
  // Hindari fetch ulang kalau data akun yang sama sudah ada (kecuali dipaksa).
  if (!force && Upload.uploadedDatesAccountId === acc.id) return;

  try {
    const res = await API.get(`/api/history/uploaded-dates?account_id=${acc.id}`);
    // Pastikan akun belum berganti selama menunggu respons (hindari data basi).
    const stillSame = (typeof state !== "undefined" && state.selectedAccount && state.selectedAccount.id === acc.id);
    if (!stillSame) return;
    Upload.uploadedDates = (res && res.counts) ? res.counts : {};
    Upload.uploadedDatesAccountId = acc.id;
  } catch (err) {
    // Kalau gagal, jangan ganggu alur — cukup kosongkan penanda.
    Upload.uploadedDates = {};
    Upload.uploadedDatesAccountId = acc.id;
  }
  // Render ulang kalender bila panelnya sedang tampil.
  if (document.getElementById("calPicker")) renderCalendar();
  // Perbarui juga kotak info tanggal terpilih (tombol hapus catatan). v1.1.21
  if (document.getElementById("dateUploadedInfo")) updateDateUI();
}

function renderCalendar() {
  const host = document.getElementById("calPicker");
  if (!host) return;

  const year = Upload.calYear;
  const month = Upload.calMonth; // 0-11

  // Hari pertama bulan ini jatuh di kolom mana (0=Minggu .. 6=Sabtu)
  const firstDow = new Date(year, month, 1).getDay();
  // Jumlah hari dalam bulan (trik: hari ke-0 bulan berikutnya = hari terakhir bulan ini)
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const todayStr = todayISO();
  const dowHeader = ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"]
    .map((d) => `<div class="cal-dow">${d}</div>`)
    .join("");

  let cells = "";
  // sel kosong sebelum tanggal 1
  for (let i = 0; i < firstDow; i++) {
    cells += `<div class="cal-cell empty"></div>`;
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const iso = `${year}-${pad2(month + 1)}-${pad2(day)}`;
    const classes = ["cal-cell"];
    if (iso === todayStr) classes.push("today");
    if (iso === Upload.batchDate) classes.push("selected");
    // Penanda hijau: akun ini SUDAH pernah upload di tanggal ini (v1.1.21)
    const uploadCount = Upload.uploadedDates ? Upload.uploadedDates[iso] : 0;
    let title = "";
    if (uploadCount) {
      classes.push("has-upload");
      title = ` title="Sudah upload ${uploadCount} video di tanggal ini"`;
    }
    const dot = uploadCount ? `<span class="cal-upload-dot"></span>` : "";
    cells += `<div class="${classes.join(" ")}" data-date="${iso}"${title}>${day}${dot}</div>`;
  }

  host.innerHTML = `
    <div class="cal-header">
      <div class="cal-nav" id="calPrev" title="Bulan sebelumnya">‹</div>
      <div class="cal-title">${BULAN_ID[month]} ${year}</div>
      <div class="cal-nav" id="calNext" title="Bulan berikutnya">›</div>
    </div>
    <div class="cal-grid">
      ${dowHeader}
      ${cells}
    </div>`;

  // navigasi bulan
  host.querySelector("#calPrev").onclick = () => {
    Upload.calMonth--;
    if (Upload.calMonth < 0) { Upload.calMonth = 11; Upload.calYear--; }
    renderCalendar();
  };
  host.querySelector("#calNext").onclick = () => {
    Upload.calMonth++;
    if (Upload.calMonth > 11) { Upload.calMonth = 0; Upload.calYear++; }
    renderCalendar();
  };

  // pilih tanggal
  host.querySelectorAll("[data-date]").forEach((cell) => {
    cell.onclick = () => {
      Upload.batchDate = cell.dataset.date;
      updateDateUI();
      renderCalendar();
    };
  });
}

// Perbarui kotak "Tanggal Terpilih" tanpa render ulang seluruh panel
function updateDateUI() {
  const val = document.getElementById("dateSelectedValue");
  const sub = document.getElementById("dateSelectedSub");
  if (val) {
    if (Upload.batchDate) {
      val.textContent = formatBatchDateLong(Upload.batchDate);
      val.classList.remove("empty");
    } else {
      val.textContent = "Belum dipilih";
      val.classList.add("empty");
    }
  }
  if (sub && Upload.batchDate) sub.textContent = Upload.batchDate;

  // Info + tombol hapus catatan bila tanggal terpilih SUDAH ada upload (v1.1.21)
  const info = document.getElementById("dateUploadedInfo");
  if (info) {
    const cnt = (Upload.batchDate && Upload.uploadedDates) ? Upload.uploadedDates[Upload.batchDate] : 0;
    if (cnt) {
      info.innerHTML = `
        <div style="background:rgba(46,204,113,.08);border:1px solid rgba(46,204,113,.35);border-radius:8px;padding:9px 11px;font-size:12px;line-height:1.5">
          <div style="color:#2ecc71;font-weight:600;margin-bottom:2px">● Sudah upload di tanggal ini</div>
          <div class="muted" style="margin-bottom:8px">Akun ini tercatat sudah mengupload <b>${cnt}</b> video pada ${escapeHtml(formatBatchDateLong(Upload.batchDate))}. Kamu tetap bisa upload lagi di tanggal ini bila perlu.</div>
          <button class="btn btn-ghost btn-sm" id="btnClearDateRecord" style="color:var(--danger,#ff6b6b);font-size:11.5px">🗑️ Hapus catatan tanggal ini</button>
        </div>`;
      const btn = document.getElementById("btnClearDateRecord");
      if (btn) btn.onclick = () => confirmClearDateRecord(Upload.batchDate, cnt);
    } else {
      info.innerHTML = "";
    }
  }
}

// Konfirmasi & hapus catatan upload sebuah tanggal (untuk akun terpilih). v1.1.21
function confirmClearDateRecord(date, count) {
  const acc = (typeof state !== "undefined" && state.selectedAccount) ? state.selectedAccount : null;
  if (!acc || !date) return;
  Modal.open({
    title: "Hapus Catatan Tanggal Ini?",
    bodyHtml: `<div style="font-size:13px;line-height:1.6">
      Hapus catatan upload untuk <b>${escapeHtml(acc.username)}</b> pada tanggal <b>${escapeHtml(formatBatchDateLong(date))}</b>?
      <div class="muted" style="margin-top:8px">Ini menghapus <b>${count}</b> catatan video dari riwayat aplikasi sehingga penanda hijau tanggal itu hilang. Berguna kalau jadwalnya dibatalkan/salah.</div>
      <div class="muted" style="margin-top:8px;font-size:11.5px">Catatan: ini <b>tidak</b> menghapus apa pun di HP atau di TikTok Studio — pembatalan jadwal di TikTok Studio dilakukan sendiri di aplikasi TikTok.</div>
    </div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: "Ya, Hapus Catatan", class: "btn btn-danger",
        onClick: async () => {
          try {
            const res = await API.del("/api/history/uploaded-dates", { account_id: acc.id, date });
            Modal.close();
            toast(`Catatan tanggal dihapus (${res.deleted_videos || 0} video)`, "success");
            await loadUploadedDates(true);
            updateDateUI();
            if (typeof loadRecentHistory === "function") loadRecentHistory();
          } catch (err) {
            toast(err.error || "Gagal menghapus catatan", "error");
          }
        },
      },
    ],
  });
}

// ════════════════════════════════════════
// EMPAT SUMBER VIDEO TETAP (v1.31)
// ════════════════════════════════════════
function getSelectedVideoSource() {
  return Upload.videoSources.find((source) => Number(source.id) === Number(Upload.sourceId)) || null;
}

async function loadVideoSources() {
  try {
    const res = await API.get("/api/upload/sources");
    Upload.videoSources = Array.isArray(res.sources) ? res.sources : [];
    Upload.sourceRoot = res.root_path || window.RemoteHPStoragePath || "";
    let selected = getSelectedVideoSource();
    if (!selected && Upload.videoSources.length) {
      Upload.sourceId = Number(Upload.videoSources[0].id);
      selected = Upload.videoSources[0];
    }
    Upload.folderPath = selected ? selected.path : null;
    renderVideoSourceGrid();
  } catch (err) {
    Upload.videoSources = [];
    const grid = document.getElementById("videoSourceGrid");
    if (grid) grid.innerHTML = `<div class="video-source-error">${escapeHtml(err.error || "Folder sumber tidak dapat dimuat")}</div>`;
    const root = document.getElementById("videoSourceRoot");
    if (root) root.querySelector("span").textContent = "Root sumber belum valid. Periksa menu Pengaturan.";
    updateVideoSourceScanButton();
  }
}

function renderVideoSourceGrid() {
  const grid = document.getElementById("videoSourceGrid");
  if (!grid) return;
  if (!Upload.videoSources.length) {
    grid.innerHTML = `<div class="video-source-loading"><span class="spinner"></span> Memuat folder sumber...</div>`;
    updateVideoSourceScanButton();
    return;
  }
  grid.innerHTML = Upload.videoSources.map((source) => {
    const active = Number(source.id) === Number(Upload.sourceId);
    const videoCount = Number(source.video_count || 0);
    const batchCount = Number(source.subfolder_count || 0);
    const summary = videoCount > 0 ? `${videoCount} video${batchCount > 0 ? ` · ${batchCount} batch` : ""}` : "Folder kosong";
    // v1.43: tampilkan akun mana saja yang sedang punya sesi aktif di sumber ini,
    // supaya kelihatan dari awal (sebelum scan) kalau folder ini sedang dipakai.
    const currentAccId = state.selectedAccount ? state.selectedAccount.id : null;
    const otherSessions = (source.active_sessions || []).filter((s) => s.account_id !== currentAccId);
    const inUseBadge = otherSessions.length
      ? `<span class="video-source-inuse">🔒 Dipakai: ${otherSessions.map((s) => escapeHtml(s.username)).join(", ")}</span>`
      : "";
    return `<button type="button" class="video-source-card ${active ? "active" : ""}" data-source-id="${source.id}" title="${escapeHtml(source.path)}" aria-pressed="${active}">
      <span class="video-source-icon">🎬</span>
      <span class="video-source-copy"><strong>${escapeHtml(source.label)}</strong><small>${escapeHtml(source.dirname)}</small></span>
      <span class="video-source-summary">${escapeHtml(summary)}</span>
      ${inUseBadge}
      <span class="video-source-check" aria-hidden="true">✓</span>
    </button>`;
  }).join("");
  grid.querySelectorAll("[data-source-id]").forEach((button) => {
    button.onclick = () => selectVideoSource(Number(button.dataset.sourceId));
  });
  const root = document.getElementById("videoSourceRoot");
  if (root) root.querySelector("span").innerHTML = `Root sumber: <b>${escapeHtml(Upload.sourceRoot || "—")}</b>`;
  updateVideoSourceScanButton();
}

function selectVideoSource(sourceId) {
  const source = Upload.videoSources.find((item) => Number(item.id) === Number(sourceId));
  if (!source) return;
  Upload.sourceId = Number(source.id);
  Upload.folderPath = source.path;
  Upload.scanResult = null;
  Upload.subfolderName = null;
  Upload.subfolderPath = null;
  const area = document.getElementById("scanResultArea");
  if (area) area.innerHTML = "";
  renderVideoSourceGrid();
}

function updateVideoSourceScanButton() {
  const button = document.getElementById("btnScanFolder");
  if (!button) return;
  const source = getSelectedVideoSource();
  button.disabled = !source;
  button.textContent = source ? `🔍 Scan ${source.label}` : "🔍 Pilih sumber dulu";
}

// ════════════════════════════════════════
// SCAN folder
// ════════════════════════════════════════
async function scanFolder() {
  // Panel 1 wajib: tanggal harus dipilih sebelum scan.
  if (!Upload.batchDate) {
    return toast("Pilih tanggal dulu di Panel 1 (bisa klik 'Hari Ini')", "warning");
  }
  const source = getSelectedVideoSource();
  if (!source) return toast("Pilih salah satu sumber video dulu", "warning");
  const folderPath = source.path;
  Upload.folderPath = folderPath;

  const btn = document.getElementById("btnScanFolder");
  btn.textContent = "⏳ Scanning...";
  btn.disabled = true;

  try {
    const res = await API.post("/api/upload/scan", {
      folder_path: folderPath,
      batch_date: Upload.batchDate,
      account_id: state.selectedAccount ? state.selectedAccount.id : null,
    });
    Upload.scanResult = res;
    renderScanResult(res);
  } catch (err) {
    toast(err.error || "Gagal scan folder", "error");
  } finally {
    updateVideoSourceScanButton();
    btn.disabled = false;
  }
}

function renderScanResult(res) {
  const area = document.getElementById("scanResultArea");
  if (!area) return;

  if (res.all_done) {
    const skipList = (res.skipped_subfolders || [])
      .map((s) => `<li><b>${escapeHtml(s.name)}/</b> — ${escapeHtml(s.message || s.reason)}</li>`)
      .join("");
    area.innerHTML = `<div class="card mt-16"><div class="card-body">
      <div class="empty-state">
        <div class="emoji">🎉</div>
        <div class="title">Tidak ada subfolder yang siap</div>
        <div class="desc">${escapeHtml(res.message || "Tidak ada video tersisa untuk diupload.")}</div>
        ${skipList ? `<ul class="scan-skip-list">${skipList}</ul>` : ""}
      </div></div></div>`;
    return;
  }

  Upload.subfolderName = res.next_subfolder;
  Upload.subfolderPath = res.subfolder_path;

  // v1.45: peta alasan skip per subfolder (dari auto-skip server), untuk
  // ditampilkan sebagai tooltip/badge di tag subfolder yang bersangkutan.
  const skipReasonByName = {};
  (res.skipped_subfolders || []).forEach((s) => { skipReasonByName[s.name] = s; });

  // info subfolder
  let subfoldersInfo = "";
  if (res.has_subfolders && res.subfolders.length) {
    subfoldersInfo = res.subfolders
      .map((sf) => {
        let cls = "tag-gray";
        let mark = "";
        let label = `${escapeHtml(sf.name)}/ (${sf.video_count})`;
        let title = "";
        const skipInfo = skipReasonByName[sf.name];
        if (sf.processed) {
          cls = "tag-green";
          mark = "✓";
        } else if (sf.locked) {
          cls = "tag-locked";
          mark = "🔒";
          label += sf.locked_by ? ` — dipakai ${escapeHtml(sf.locked_by)}` : " — dipakai akun lain";
          title = "Sedang dipakai sesi aktif akun lain — tunggu selesai/dibatalkan";
        } else if (sf.name === res.next_subfolder) {
          cls = "tag-blue";
          mark = "▶";
        } else if (skipInfo && skipInfo.reason === "video_count_mismatch") {
          cls = "tag-skip";
          mark = "⏭";
          title = skipInfo.message || "Jumlah video tidak sesuai kriteria sesi, dilewati otomatis";
        } else if (skipInfo && skipInfo.reason === "empty") {
          cls = "tag-skip";
          mark = "⏭";
          title = "Folder kosong, dilewati otomatis";
        }
        return `<span class="tag ${cls}" style="margin:2px" title="${escapeHtml(title)}">${mark} ${label}</span>`;
      })
      .join("");
  }

  // Ringkasan singkat kalau ada subfolder yang dilewati otomatis sebelum
  // sampai ke subfolder yang dipakai sekarang — supaya jelas ini BUKAN bug,
  // melainkan hasil auto-skip yang disengaja.
  const skippedBeforeChosen = (res.skipped_subfolders || []).filter(
    (s) => s.reason !== "processed" // "sudah selesai" tidak perlu ditonjolkan, itu wajar
  );
  const skipSummaryHtml = skippedBeforeChosen.length
    ? `<div class="scan-skip-note">⏭ Melewati otomatis: ${skippedBeforeChosen
        .map((s) => `<b>${escapeHtml(s.name)}/</b> (${escapeHtml(s.message || s.reason)})`)
        .join(", ")}</div>`
    : "";

  const videosHtml = res.videos
    .map((v) => {
      const dupBadge = v.is_duplicate
        ? `<div class="video-status" style="background:rgba(239,68,68,0.15);color:var(--danger)">⚠ Sudah diupload</div>`
        : `<div class="video-status waiting">Siap</div>`;
      return `<div class="video-item">
        <div class="video-thumb">🎬</div>
        <div class="video-name">${escapeHtml(v.name)}</div>
        <div class="video-size">${escapeHtml(v.size_human)}</div>
        ${dupBadge}
      </div>`;
    })
    .join("");

  const canStart = res.can_start === true;
  const sessionSize = Number(res.posts_per_session || POSTS_PER_SESSION);
  const validationHtml = !canStart && res.validation_error
    ? `<div class="batch-validation-error">⚠ ${escapeHtml(res.validation_error)}</div>`
    : "";
  const remainderHtml = canStart && Number(res.remaining_count || 0) > 0
    ? `<div class="muted" style="font-size:12px;margin-top:8px">Folder flat memiliki ${Number(res.remaining_count)} video tambahan. Sesi ini mengambil ${sessionSize} video pertama.</div>`
    : "";

  area.innerHTML = `
    <div class="card mt-16">
      <div class="card-header">
        <div class="card-title">
          <div class="step-badge done">✓</div>
          Subfolder: <span class="mono" style="color:var(--success)">${escapeHtml(res.next_subfolder)}/</span>
        </div>
        <div class="tag ${canStart ? "tag-blue" : "tag-gray"}">${canStart ? `${sessionSize} video siap` : `${Number(res.available_count || 0)}/${sessionSize} video siap`}${res.duplicate_count > 0 ? ` · ${res.duplicate_count} duplikat` : ""}</div>
      </div>
      <div class="card-body">
        ${subfoldersInfo ? `<div style="margin-bottom:12px">${subfoldersInfo}</div>` : ""}
        ${skipSummaryHtml}
        ${validationHtml}
        <div class="video-queue">${videosHtml}</div>
        ${remainderHtml}
        <div class="mt-16 flex gap-8">
          <button class="btn btn-primary" id="btnStartSession" ${canStart ? "" : "disabled"}>
            ▶️ Mulai Sesi Upload (${sessionSize} video)
          </button>
          ${
            res.duplicate_count > 0
              ? `<span style="font-size:12px;color:var(--muted);line-height:34px">${res.duplicate_count} video duplikat akan dilewati otomatis</span>`
              : ""
          }
        </div>
      </div>
    </div>`;

  if (canStart) {
    document.getElementById("btnStartSession").onclick = startSession;
  }
}

// ════════════════════════════════════════
// START session
// ════════════════════════════════════════
async function startSession() {
  const btn = document.getElementById("btnStartSession");
  btn.textContent = "⏳ Memulai...";
  btn.disabled = true;

  try {
    const res = await API.post("/api/upload/start", {
      account_id: state.selectedAccount.id,
      device_id: state.selectedDevice.id,
      folder_path: Upload.folderPath,
      subfolder: Upload.subfolderName,
      subfolder_path: Upload.subfolderPath,
      batch_date: Upload.batchDate,
    });
    Upload.session = res;
    Upload.consoleLines = [];
    if (res.skipped_duplicates > 0) {
      toast(`${res.skipped_duplicates} video duplikat dilewati`, "info");
    }
    toast("Sesi upload dimulai ✓", "success");
    renderWorkflow();
  } catch (err) {
    toast(err.error || "Gagal memulai sesi", "error");
    if (err.active_session_id) {
      // ada sesi aktif → resume
      resumeSession(err.active_session_id);
    }
    btn.textContent = "▶️ Mulai Sesi Upload";
    btn.disabled = false;
  }
}

async function resumeSession(sessionId) {
  try {
    const res = await API.get(`/api/upload/state/${sessionId}`);
    if (res.ok && res.videos) {
      const bd = res.session && res.session.batch_date ? res.session.batch_date : null;
      if (bd) Upload.batchDate = bd;
      // generate caption/schedule ulang untuk tampilan (data inti = videos)
      Upload.session = {
        session_id: sessionId,
        videos: res.videos,
        caption: { content: "(caption sebelumnya)", hashtags: "", full: "" },
        schedule: [],
        target_dir: "",
        batch_date: bd,
      };
      toast("Melanjutkan sesi yang masih aktif", "info");
      renderWorkflow();
    }
  } catch (e) {
    /* ignore */
  }
}

// ════════════════════════════════════════
// RENDER WORKFLOW (sesi aktif) — wizard step 2,3,4,5 + action bar
// ════════════════════════════════════════
function renderWorkflow() {
  const panel = document.getElementById("uploadPanelLeft");
  const s = Upload.session;
  const videos = s.videos;

  const doneCount = videos.filter((v) => v.status === "done").length;
  const total = videos.length;
  const allDone = doneCount === total;
  const progressPct = total ? Math.round((doneCount / total) * 100) : 0;

  // index video "current" = video pertama yang belum done
  const currentIndex = videos.findIndex((v) => v.status !== "done");

  // STEP 2: video queue
  const videosHtml = videos
    .map((v, i) => {
      let statusBadge;
      if (v.status === "done") statusBadge = `<div class="video-status done">✓ Selesai</div>`;
      else if (v.status === "sent") statusBadge = `<div class="video-status sent">Terkirim</div>`;
      else statusBadge = `<div class="video-status waiting">Menunggu</div>`;
      const isCurrent = i === currentIndex;
      return `<div class="video-item ${isCurrent ? "current" : ""}">
        <div class="video-thumb">🎬</div>
        <div class="video-name">${escapeHtml(v.name)}</div>
        <div class="video-size">${escapeHtml(v.size_human || "")}</div>
        ${statusBadge}
      </div>`;
    })
    .join("");

  // tombol aksi per video (kirim / konfirmasi)
  // Konfirmasi dibuka setelah Copy Semua atau Tempel ke HP berhasil.
  const captionCopiedForCurrent =
    currentIndex >= 0 && Upload.captionCopiedVideoIndex === currentIndex;
  const captionPastedForCurrent =
    currentIndex >= 0 && Upload.captionPastedVideoIndex === currentIndex;
  const captionProcessedForCurrent = captionCopiedForCurrent || captionPastedForCurrent;
  const captionConfirmDelayPending =
    captionPastedForCurrent &&
    Upload.captionConfirmUnlockVideoIndex === currentIndex &&
    Date.now() < Upload.captionConfirmUnlockAt;
  const captionConfirmDelaySeconds = captionConfirmDelayPending
    ? Math.max(1, Math.ceil((Upload.captionConfirmUnlockAt - Date.now()) / 1000))
    : 0;
  const captionReadyForCurrent = captionProcessedForCurrent && !captionConfirmDelayPending;
  const currentScheduleTime = currentIndex >= 0 && s.schedule && s.schedule[currentIndex]
    ? String(s.schedule[currentIndex].time || "").trim()
    : "";
  let actionButtons = "";
  if (!allDone && currentIndex >= 0) {
    const cur = videos[currentIndex];
    const num = currentIndex + 1;
    if (cur.status === "waiting") {
      actionButtons = `<button class="btn btn-primary" id="btnPushVideo">📤 Kirim Video ${num} ke HP</button>`;
    } else if (cur.status === "sent") {
      const confirmLabel = currentScheduleTime
        ? `✓ Selesai - ${escapeHtml(currentScheduleTime)}`
        : "✓ Selesai";
      const confirmHint = captionConfirmDelayPending
        ? `Caption sudah dikirim. Tombol Selesai aktif dalam ${captionConfirmDelaySeconds} detik.`
        : captionPastedForCurrent
          ? "Caption sudah dikirim ke HP. Periksa hasilnya di layar lalu selesaikan upload."
          : captionCopiedForCurrent
            ? "Caption sudah disalin. Tempel manual di HP lalu selesaikan upload."
            : "Klik Tempel ke HP atau Copy Semua di Panel 3 sebelum menandai video selesai.";
      const confirmTitle = captionConfirmDelayPending
        ? `Tunggu ${captionConfirmDelaySeconds} detik setelah caption ditempel`
        : captionReadyForCurrent
          ? "Tandai video selesai"
          : "Tempel atau salin caption terlebih dahulu";
      actionButtons = `<span class="workflow-action-hint">${confirmHint}</span>
        <button class="btn btn-success" id="btnConfirmVideo"
          ${captionReadyForCurrent ? "" : "disabled"}
          title="${confirmTitle}">${confirmLabel}</button>`;
    }
  }

  // console
  const consoleHtml = Upload.consoleLines.length
    ? Upload.consoleLines
        .map((line) => {
          if (line.type === "cmd") return `<div><span class="cmd">$</span> ${escapeHtml(line.text)}</div>`;
          if (line.type === "ok") return `<div style="color:#4ade80">${escapeHtml(line.text)}</div>`;
          if (line.type === "error") return `<div style="color:#f87171">${escapeHtml(line.text)}</div>`;
          if (line.type === "warn") return `<div style="color:#fbbf24">${escapeHtml(line.text)}</div>`;
          return `<div>${escapeHtml(line.text)}</div>`;
        })
        .join("")
    : `<div class="cmd">Menunggu perintah...</div>`;

  // caption
  const cap = s.caption || {};
  const captionIsEmpty = !!cap.empty || !(cap.full || cap.content || cap.hashtags);
  const copyButtonClass = captionCopiedForCurrent ? "btn btn-success btn-sm" : "btn btn-ghost btn-sm";
  const copyButtonLabel = captionCopiedForCurrent ? "✓ Sudah Disalin" : "📋 Copy Semua";
  const pasteButtonClass = captionPastedForCurrent ? "btn btn-success btn-sm" : "btn btn-primary btn-sm";
  const pasteButtonLabel = captionPastedForCurrent ? "✓ Sudah Ditempel" : "📱 Tempel ke HP";
  const pasteButtonCoolingDown = Date.now() < Upload.captionPasteCooldownUntil;
  const pasteButtonEnabled =
    currentIndex >= 0 &&
    videos[currentIndex].status === "sent" &&
    !pasteButtonCoolingDown;
  const captionHtml = cap.empty
    ? `<div class="muted">Belum ada template caption. Tambahkan di Pengaturan.</div>`
    : `<div class="caption-box">${escapeHtml(cap.content)}${
        cap.hashtags ? `<br><br><span class="caption-hashtag">${escapeHtml(cap.hashtags)}</span>` : ""
      }</div>`;

  // STEP 4: Mode Cepat — satu panel wizard untuk tiga aksi utama.
  // Tahap 1: hanya Kirim Video terlihat di kanan.
  // Tahap 2: tombol kirim menjadi selesai/disabled dan Isi Caption muncul.
  // Tahap 3: dua tombol sebelumnya menjadi selesai/disabled dan Selesai muncul.
  let quickStage = 4; // 4 = seluruh antrean selesai
  if (!allDone && currentIndex >= 0) {
    const quickCurrent = videos[currentIndex];
    if (quickCurrent.status === "waiting") quickStage = 1;
    else if (!captionProcessedForCurrent) quickStage = 2;
    else quickStage = 3;
  }

  const previousQuickStage = Upload.quickModeRenderedIndex === currentIndex
    ? Upload.quickModeRenderedStage
    : quickStage;
  const quickStartStage = Number.isInteger(previousQuickStage) && previousQuickStage < quickStage
    ? previousQuickStage
    : quickStage;
  Upload.quickModeRenderedIndex = currentIndex;
  Upload.quickModeRenderedStage = quickStage;

  const quickPostNumber = currentIndex >= 0 ? currentIndex + 1 : total;
  const quickFinishLabel = currentScheduleTime
    ? `✓ Selesai - ${escapeHtml(currentScheduleTime)}`
    : "✓ Selesai";
  const quickCaptionDoneLabel = captionPastedForCurrent
    ? "✓ Caption Diisi"
    : "✓ Caption Disalin";
  const quickCaptionCanRun = quickStage === 2 && !pasteButtonCoolingDown;
  const quickModeHtml = allDone
    ? `<div class="quick-mode-complete">
         <div class="quick-mode-complete-icon">✓</div>
         <div>
           <strong>Semua video selesai</strong>
           <span>Mode Cepat sudah menuntaskan ${total} post. Lanjutkan dengan Selesai Sesi.</span>
         </div>
       </div>`
    : `<div class="quick-mode-copy">
         <strong>Post ${quickPostNumber} dari ${total}</strong>
         <span>${quickStage === 1
           ? "Mulai dengan mengirim video aktif ke HP. Caption akan dibuat ulang otomatis."
           : quickStage === 2
             ? "Aktifkan kolom caption di TikTok, lalu klik Isi Caption."
             : "Periksa hasil upload di layar HP, lalu tandai post ini selesai."}</span>
       </div>
       <div class="quick-mode-actions" id="quickModeActions"
         data-stage="${quickStartStage}" data-target-stage="${quickStage}">
         <button class="btn ${quickStage >= 2 ? "btn-success quick-mode-done" : "btn-primary"} quick-mode-step quick-mode-step-1"
           id="btnQuickPushVideo" ${quickStage === 1 ? "" : "disabled"}
           title="${quickStage === 1 ? `Kirim video ${quickPostNumber} ke HP` : `Video ${quickPostNumber} sudah terkirim`}">
           ${quickStage === 1 ? `📤 Kirim Video ${quickPostNumber} ke HP` : `✓ Video ${quickPostNumber} Terkirim`}
         </button>
         <button class="btn ${quickStage >= 3 ? "btn-success quick-mode-done" : "btn-primary"} quick-mode-step quick-mode-step-2"
           id="btnQuickFillCaption" ${quickCaptionCanRun ? "" : "disabled"}
           title="${quickStage === 2
             ? pasteButtonCoolingDown
               ? "Tunggu sebentar untuk mencegah caption tertempel dua kali"
               : captionIsEmpty
                 ? "Caption kosong akan dibuat ulang otomatis, maksimal 3 kali"
                 : "Tempel caption ke kolom aktif di TikTok"
             : quickStage >= 3 ? "Caption untuk post ini sudah diproses" : "Kirim video terlebih dahulu"}">
           ${quickStage >= 3 ? quickCaptionDoneLabel : "📱 Isi Caption"}
         </button>
         <button class="btn btn-success quick-mode-step quick-mode-step-3"
           id="btnQuickConfirmVideo" ${quickStage === 3 && captionReadyForCurrent ? "" : "disabled"}
           title="${quickStage === 3
             ? captionConfirmDelayPending
               ? `Tunggu ${captionConfirmDelaySeconds} detik setelah caption ditempel`
               : "Tandai post ini selesai"
             : "Isi caption terlebih dahulu"}">
           ${quickFinishLabel}
         </button>
       </div>`;

  // schedule — tiap kolom jam mengikuti status video di indeks yang sama.
  // Sudah selesai upload → hijau; sedang berlangsung → biru "berlangsung";
  // sisanya menunggu. Penanda ini mencegah jam upload dobel & memperjelas urutan.
  const scheduleHtml = (s.schedule || [])
    .map((sc, i) => {
      const vid = videos[i];
      const vidName = vid ? vid.name : "";
      let stateClass = "waiting";
      let statusTag = `<div class="schedule-status waiting">Menunggu</div>`;
      if (vid && vid.status === "done") {
        stateClass = "done";
        statusTag = `<div class="schedule-status done">✓ Selesai</div>`;
      } else if (i === currentIndex) {
        stateClass = "current";
        statusTag = `<div class="schedule-status current">● Berlangsung</div>`;
      }
      return `<div class="schedule-item ${stateClass}">
        <div style="min-width:0">
          <div class="schedule-label">${escapeHtml(sc.label)}</div>
          <div class="schedule-time">${escapeHtml(sc.time)}</div>
          <div class="schedule-vid">${escapeHtml(vidName)}</div>
          ${statusTag}
        </div>
        <button class="btn btn-ghost icon-btn" data-copy-time="${escapeHtml(sc.time)}">📋</button>
      </div>`;
    })
    .join("");

  panel.innerHTML = `
    <!-- STEP 2: VIDEO QUEUE -->
    <div class="card">
      <div class="card-header">
        <div class="card-title"><div class="step-badge ${allDone ? "done" : ""}">2</div> Video — Kirim Satu per Satu (FIFO)</div>
        <div class="card-header-actions">
          <button class="btn btn-ghost btn-sm panel-visibility-toggle" id="btnToggleConsole"
            aria-expanded="${Upload.consoleHidden ? "false" : "true"}"
            title="${Upload.consoleHidden ? "Tampilkan kolom log" : "Sembunyikan kolom log"}">
            ${Upload.consoleHidden ? "👁 Tampilkan Log" : "🙈 Sembunyikan Log"}
          </button>
          <div class="tag ${allDone ? "tag-green" : "tag-blue"}">${doneCount}/${total} selesai</div>
        </div>
      </div>
      <div class="card-body">
        <div class="video-queue">${videosHtml}</div>
        ${actionButtons ? `<div class="workflow-video-actions mt-16">${actionButtons}</div>` : ""}
        <div class="adb-console mt-16" id="adbConsole" ${Upload.consoleHidden ? "hidden" : ""}>${consoleHtml}</div>
      </div>
    </div>

    <!-- STEP 3: CAPTION -->
    <div class="card">
      <div class="card-header">
        <div class="card-title"><div class="step-badge">3</div> Caption & Hashtag</div>
        <div class="card-header-actions">
          <button class="btn btn-ghost btn-sm panel-visibility-toggle" id="btnToggleCaptionPreview"
            aria-expanded="${Upload.captionPreviewHidden ? "false" : "true"}"
            title="${Upload.captionPreviewHidden ? "Tampilkan teks caption dan hashtag" : "Sembunyikan teks caption dan hashtag"}">
            ${Upload.captionPreviewHidden ? "👁 Tampilkan Teks" : "🙈 Sembunyikan Teks"}
          </button>
          <button class="btn btn-ghost btn-sm" id="btnRegenCaption">🔀 Generate Ulang</button>
          <button class="${copyButtonClass}" id="btnCopyAll" ${captionIsEmpty ? "disabled" : ""}>${copyButtonLabel}</button>
          <button class="${pasteButtonClass}" id="btnPasteToPhone"
            ${pasteButtonEnabled ? "" : "disabled"}
            title="${pasteButtonEnabled
              ? captionIsEmpty
                ? "Caption kosong akan dibuat ulang otomatis, maksimal 3 kali"
                : "Fokuskan kolom caption di TikTok, lalu klik"
              : pasteButtonCoolingDown
                ? "Tunggu sebentar untuk mencegah caption tertempel dua kali"
                : "Kirim video ke HP terlebih dahulu"}">${pasteButtonLabel}</button>
        </div>
      </div>
      <div class="card-body" id="captionPreviewBody" ${Upload.captionPreviewHidden ? "hidden" : ""}>${captionHtml}</div>
    </div>

    <!-- STEP 4: MODE CEPAT -->
    <div class="card quick-mode-card">
      <div class="card-header">
        <div class="card-title"><div class="step-badge ${allDone ? "done" : ""}">4</div> Mode Cepat</div>
        <div class="quick-mode-header-meta">
          ${allDone ? "" : `<div class="quick-mode-current-time">${escapeHtml(currentScheduleTime || "--:--")}</div>`}
        </div>
      </div>
      <div class="card-body quick-mode-body">${quickModeHtml}</div>
    </div>

    <!-- STEP 5: JADWAL -->
    <div class="card">
      <div class="card-header">
        <div class="card-title"><div class="step-badge">5</div> Jadwal Post (TikTok Studio)</div>
        <button class="btn btn-ghost btn-sm" id="btnRegenSchedule">🔀 Generate Ulang</button>
      </div>
      <div class="card-body">
        ${
          s.batch_date
            ? `<div class="flex gap-8" style="align-items:center;margin-bottom:12px">
                 <span class="tag tag-blue">📅 ${escapeHtml(formatBatchDateLong(s.batch_date))}</span>
                 <span class="muted" style="font-size:11.5px">Set semua post ke tanggal ini di TikTok Studio</span>
               </div>`
            : ""
        }
        <div class="schedule-grid">${scheduleHtml || '<div class="muted">—</div>'}</div>
      </div>
    </div>

    <!-- ACTION BAR -->
    <div class="action-bar" style="border-radius:10px;border:1px solid var(--border)">
      <div class="progress-bar-wrap">
        <div class="progress-label">${doneCount} dari ${total} video selesai diupload</div>
        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:${progressPct}%"></div></div>
      </div>
      <button class="btn btn-danger" id="btnCancelSession">✕ Batal</button>
      <button class="btn btn-success" id="btnFinishSession" ${allDone ? "" : "disabled"}>
        🎉 Selesai Sesi
      </button>
    </div>`;

  bindWorkflowEvents();
  // auto-scroll console ke bawah
  const con = document.getElementById("adbConsole");
  if (con) con.scrollTop = con.scrollHeight;
}

function bindWorkflowEvents() {
  const btnPush = document.getElementById("btnPushVideo");
  if (btnPush) btnPush.onclick = pushCurrentVideo;
  const btnConfirm = document.getElementById("btnConfirmVideo");
  if (btnConfirm) btnConfirm.onclick = confirmCurrentVideo;

  // Mode Cepat memakai fungsi inti yang sama agar state, guard, histori,
  // generate caption, dan penghapusan video tetap satu sumber kebenaran.
  const btnQuickPush = document.getElementById("btnQuickPushVideo");
  if (btnQuickPush) btnQuickPush.onclick = pushCurrentVideo;
  const btnQuickCaption = document.getElementById("btnQuickFillCaption");
  if (btnQuickCaption) btnQuickCaption.onclick = () => pasteCaptionToPhone((Upload.session.caption || {}).full || "");
  const btnQuickConfirm = document.getElementById("btnQuickConfirmVideo");
  if (btnQuickConfirm) btnQuickConfirm.onclick = confirmCurrentVideo;

  const quickActions = document.getElementById("quickModeActions");
  if (quickActions && quickActions.dataset.stage !== quickActions.dataset.targetStage) {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (quickActions.isConnected) quickActions.dataset.stage = quickActions.dataset.targetStage;
    }));
  }

  const btnToggleConsole = document.getElementById("btnToggleConsole");
  if (btnToggleConsole) btnToggleConsole.onclick = () => {
    Upload.consoleHidden = !Upload.consoleHidden;
    renderWorkflow();
  };
  const btnToggleCaptionPreview = document.getElementById("btnToggleCaptionPreview");
  if (btnToggleCaptionPreview) btnToggleCaptionPreview.onclick = () => {
    Upload.captionPreviewHidden = !Upload.captionPreviewHidden;
    renderWorkflow();
  };

  const btnFinish = document.getElementById("btnFinishSession");
  if (btnFinish) btnFinish.onclick = finishSession;
  const btnCancel = document.getElementById("btnCancelSession");
  if (btnCancel) btnCancel.onclick = cancelSession;

  // caption
  const cap = Upload.session.caption || {};
  const ba = document.getElementById("btnCopyAll");
  if (ba) {
    ba.onclick = async () => {
      const idx = Upload.session.videos.findIndex((v) => v.status !== "done");
      if (idx < 0) return;
      const copied = await copyText(cap.full || "");
      if (copied) {
        Upload.captionCopiedVideoIndex = idx;
        renderWorkflow();
      }
    };
  }
  const btp = document.getElementById("btnPasteToPhone");
  if (btp) btp.onclick = () => pasteCaptionToPhone(cap.full || "");
  const brc = document.getElementById("btnRegenCaption");
  if (brc) brc.onclick = regenCaption;
  const brs = document.getElementById("btnRegenSchedule");
  if (brs) brs.onclick = regenSchedule;

  // copy schedule
  document.querySelectorAll("[data-copy-time]").forEach((b) => {
    b.onclick = () => copyText(b.dataset.copyTime);
  });
}

// ── Aksi: TEMPEL caption ke HP ──
function captionHasText(caption) {
  if (!caption || caption.empty) return false;
  return Boolean(String(caption.full || caption.content || caption.hashtags || "").trim());
}

// Fallback caption kosong: generate ulang maksimal tiga kali. Fungsi ini
// sengaja tidak memanggil dirinya sendiri agar tidak mungkin menjadi loop tak
// berujung. Percobaan berhenti segera setelah caption valid ditemukan.
async function ensureCaptionForPaste(maxAttempts = 3) {
  let current = Upload.session.caption || {};
  if (captionHasText(current)) return current;

  let lastError = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const res = await API.get("/api/upload/regen-caption");
      if (res.caption) {
        Upload.session.caption = res.caption;
        Upload.captionCopiedVideoIndex = null;
        Upload.captionPastedVideoIndex = null;
        clearCaptionConfirmDelay();
        current = res.caption;
        if (captionHasText(current)) return current;
      }
      lastError = { error: `Caption masih kosong setelah percobaan ${attempt}` };
    } catch (err) {
      lastError = err;
    }
  }

  throw {
    error: (lastError && lastError.error)
      ? `Caption gagal dibuat setelah ${maxAttempts} percobaan: ${lastError.error}`
      : `Caption gagal dibuat setelah ${maxAttempts} percobaan`,
  };
}

const CAPTION_CONFIRM_DELAY_MS = 2000;

function clearCaptionConfirmDelay() {
  if (Upload.captionConfirmUnlockTimer) {
    clearTimeout(Upload.captionConfirmUnlockTimer);
  }
  Upload.captionConfirmUnlockAt = 0;
  Upload.captionConfirmUnlockVideoIndex = null;
  Upload.captionConfirmUnlockTimer = null;
}

function startCaptionConfirmDelay(videoIndex) {
  clearCaptionConfirmDelay();
  Upload.captionConfirmUnlockVideoIndex = videoIndex;
  Upload.captionConfirmUnlockAt = Date.now() + CAPTION_CONFIRM_DELAY_MS;

  Upload.captionConfirmUnlockTimer = setTimeout(() => {
    const activeIndex = Upload.session
      ? Upload.session.videos.findIndex((v) => v.status !== "done")
      : -1;
    Upload.captionConfirmUnlockTimer = null;
    if (activeIndex !== videoIndex) return;
    Upload.captionConfirmUnlockAt = 0;
    Upload.captionConfirmUnlockVideoIndex = null;
    if (state.currentPage === "upload") renderWorkflow();
  }, CAPTION_CONFIRM_DELAY_MS + 25);
}

async function pasteCaptionToPhone(text) {
  const videos = Upload.session.videos;
  const idx = videos.findIndex((v) => v.status !== "done");
  if (idx < 0) return;

  // Cooldown minimum satu detik mencegah klik ganda menempelkan caption dua kali.
  Upload.captionPasteCooldownUntil = Date.now() + 1000;
  const pasteButtons = [
    document.getElementById("btnPasteToPhone"),
    document.getElementById("btnQuickFillCaption"),
  ].filter(Boolean);
  pasteButtons.forEach((btn) => {
    btn.disabled = true;
    btn.textContent = captionHasText(Upload.session.caption)
      ? "⏳ Menempel..."
      : "⏳ Membuat Caption...";
  });

  try {
    // Parameter lama tetap diterima, tetapi state sesi menjadi sumber utama agar
    // hasil generate fallback yang baru tidak tertimpa teks kosong dari klik awal.
    let caption = Upload.session.caption || {};
    if (!captionHasText(caption) && String(text || "").trim()) {
      caption = { ...caption, full: String(text).trim(), empty: false };
    }
    if (!captionHasText(caption)) {
      caption = await ensureCaptionForPaste(3);
      pasteButtons.forEach((btn) => {
        if (btn.isConnected) btn.textContent = "⏳ Menempel...";
      });
    }

    const captionText = String(
      caption.full || [caption.content, caption.hashtags].filter(Boolean).join("\n\n")
    ).trim();
    if (!captionText) {
      throw { error: "Caption hasil generate masih kosong" };
    }

    // Clipboard browser harus diisi saat web app masih memiliki fokus.
    const copied = await copyText(captionText, { silent: true });
    if (!copied) {
      throw { error: "Gagal menyalin caption ke clipboard PC" };
    }

    const res = await API.post("/api/upload/paste-caption", {
      session_id: Upload.session.session_id,
      index: idx,
    });
    if (!res.ok || !res.focused || !res.pasted) {
      throw { error: res.error || "Gagal mengirim Ctrl+V ke scrcpy" };
    }

    // Auto-paste juga sudah menyalin caption, sehingga kedua status valid.
    Upload.captionCopiedVideoIndex = idx;
    Upload.captionPastedVideoIndex = idx;
    startCaptionConfirmDelay(idx);
    renderWorkflow();
    toast("Caption ditempel ke HP ✓ Tombol Selesai aktif dalam 2 detik.", "success", 2400);
  } catch (err) {
    renderWorkflow();
    toast(
      err.error || "Gagal menempelkan caption. Gunakan Copy Semua sebagai fallback.",
      "error",
      5000
    );
  } finally {
    const remaining = Upload.captionPasteCooldownUntil - Date.now();
    if (remaining > 0) {
      setTimeout(() => {
        if (Upload.session && state.currentPage === "upload") renderWorkflow();
      }, remaining + 25);
    }
  }
}

// ── Aksi: PUSH video saat ini ──
async function pushCurrentVideo() {
  const videos = Upload.session.videos;
  const idx = videos.findIndex((v) => v.status !== "done");
  if (idx < 0) return;

  const pushButtons = [
    document.getElementById("btnPushVideo"),
    document.getElementById("btnQuickPushVideo"),
  ].filter(Boolean);
  pushButtons.forEach((btn) => {
    btn.textContent = "⏳ Mengirim...";
    btn.disabled = true;
  });

  try {
    const res = await API.post("/api/upload/push", {
      session_id: Upload.session.session_id,
      index: idx,
    });
    if (res.console) Upload.consoleLines.push(...res.console);
    if (res.ok) {
      Upload.session.videos = res.videos;
      // Caption yang sempat disalin sebelum proses kirim tidak boleh membuka
      // tombol selesai, karena proses kirim otomatis membuat caption baru.
      Upload.captionCopiedVideoIndex = null;
      Upload.captionPastedVideoIndex = null;
      clearCaptionConfirmDelay();

      // Sekali klik: setelah video berhasil dikirim ke HP, langsung buat
      // caption baru untuk video tersebut. Kegagalan generate caption tidak
      // membatalkan status kirim video yang sudah sukses.
      let captionUpdated = false;
      try {
        const captionRes = await API.get("/api/upload/regen-caption");
        if (captionRes.caption) {
          Upload.session.caption = captionRes.caption;
          captionUpdated = true;
        }
      } catch (captionErr) {
        console.warn("Auto-generate caption gagal:", captionErr);
      }

      if (captionUpdated) {
        toast(`Video ${idx + 1} terkirim dan caption baru dibuat ✓`, "success");
      } else {
        toast(
          `Video ${idx + 1} terkirim, tetapi caption gagal diperbarui`,
          "warning",
          5000
        );
      }
    }
    renderWorkflow();
  } catch (err) {
    if (err.console) Upload.consoleLines.push(...err.console);
    toast(err.error || "Gagal mengirim video", "error", 5000);
    renderWorkflow();
  }
}

// ── Aksi: KONFIRMASI video saat ini selesai ──
async function confirmCurrentVideo() {
  const videos = Upload.session.videos;
  const idx = videos.findIndex((v) => v.status !== "done");
  if (idx < 0) return;

  // Guard tambahan selain atribut disabled di tombol.
  const captionReady =
    Upload.captionCopiedVideoIndex === idx || Upload.captionPastedVideoIndex === idx;
  if (!captionReady) {
    toast("Klik Tempel ke HP atau Copy Semua sebelum menandai video selesai", "warning", 3500);
    renderWorkflow();
    return;
  }

  if (
    Upload.captionPastedVideoIndex === idx &&
    Upload.captionConfirmUnlockVideoIndex === idx &&
    Date.now() < Upload.captionConfirmUnlockAt
  ) {
    const seconds = Math.max(1, Math.ceil((Upload.captionConfirmUnlockAt - Date.now()) / 1000));
    toast(`Tunggu ${seconds} detik setelah caption ditempel`, "info", 1800);
    renderWorkflow();
    return;
  }

  const confirmButtons = [
    document.getElementById("btnConfirmVideo"),
    document.getElementById("btnQuickConfirmVideo"),
  ].filter(Boolean);
  confirmButtons.forEach((btn) => {
    btn.textContent = "⏳ Memproses...";
    btn.disabled = true;
  });

  try {
    const res = await API.post("/api/upload/confirm", {
      session_id: Upload.session.session_id,
      index: idx,
    });
    if (res.console) Upload.consoleLines.push(...res.console);
    Upload.session.videos = res.videos;
    // Video berikutnya wajib menempel atau menyalin captionnya sendiri.
    Upload.captionCopiedVideoIndex = null;
    Upload.captionPastedVideoIndex = null;
    clearCaptionConfirmDelay();
    if (res.all_done) {
      toast("Semua video selesai! Klik 'Selesai Sesi' 🎉", "success", 4000);
    } else {
      toast(`Video ${idx + 1} selesai. Lanjut video berikutnya.`, "success");
    }
    renderWorkflow();
    // refresh sidebar count
    loadDevices();
    if (typeof loadRecentHistory === 'function') loadRecentHistory();
    // Video sudah tercatat di histori → segarkan penanda tanggal (v1.1.21)
    loadUploadedDates(true);
  } catch (err) {
    if (err.console) Upload.consoleLines.push(...err.console);
    toast(err.error || "Gagal konfirmasi", "error");
    renderWorkflow();
  }
}

// ── Aksi: SELESAI sesi ──
async function finishSession() {
  try {
    const res = await API.post("/api/upload/finish", {
      session_id: Upload.session.session_id,
    });
    const sum = res.summary;
    Modal.open({
      title: "🎉 Sesi Selesai",
      bodyHtml: `<div style="font-size:13px;line-height:1.7">
        <div style="margin-bottom:12px"><strong>${escapeHtml(sum.account)}</strong> di ${escapeHtml(
        sum.device
      )}</div>
        <div class="muted" style="margin-bottom:8px">Subfolder <span class="mono">${escapeHtml(
          sum.subfolder
        )}/</span> — ${sum.video_count} video diupload:</div>
        <div class="adb-console" style="color:var(--text);max-height:160px">
          ${sum.videos.map((v) => `<div>✓ ${escapeHtml(v)}</div>`).join("")}
        </div>
      </div>`,
      footerButtons: [
        {
          label: "Selesai",
          class: "btn btn-primary",
          onClick: () => {
            Modal.close();
            Upload.reset();
            // paksa muat ulang penanda tanggal untuk akun ini (v1.1.21)
            Upload.uploadedDatesAccountId = null;
            renderUploadPanel();
            loadDevices();
            if (typeof loadRecentHistory === 'function') loadRecentHistory();
          },
        },
      ],
    });
  } catch (err) {
    toast(err.error || "Gagal menyelesaikan sesi", "error");
  }
}

// ── Aksi: BATAL sesi ──
async function cancelSession() {
  Modal.open({
    title: "Batalkan Sesi?",
    bodyHtml: `<div style="font-size:13px;line-height:1.6">
      Yakin batalkan sesi upload ini?<br>
      <span class="muted">Video yang sudah selesai tetap tercatat. Video yang sudah terkirim ke HP
      tapi belum dikonfirmasi perlu Anda hapus manual dari galeri HP.</span>
    </div>`,
    footerButtons: [
      { label: "Tidak", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: "Ya, Batalkan",
        class: "btn btn-danger",
        onClick: async () => {
          try {
            const res = await API.post("/api/upload/cancel", {
              session_id: Upload.session.session_id,
            });
            Modal.close();
            if (res.warning) toast(res.warning, "warning", 6000);
            else toast("Sesi dibatalkan", "info");
            Upload.reset();
            renderUploadPanel();
            loadDevices();
            if (typeof loadRecentHistory === 'function') loadRecentHistory();
          } catch (err) {
            toast(err.error || "Gagal membatalkan", "error");
          }
        },
      },
    ],
  });
}

// ── Regenerate caption ──
async function regenCaption() {
  try {
    const res = await API.get("/api/upload/regen-caption");
    if (res.caption) {
      Upload.session.caption = res.caption;
      // Caption baru harus ditempel/disalin ulang sebelum tombol selesai dibuka.
      Upload.captionCopiedVideoIndex = null;
      Upload.captionPastedVideoIndex = null;
      clearCaptionConfirmDelay();
      renderWorkflow();
      toast("Caption diperbarui", "success", 1500);
    }
  } catch (err) {
    toast(err.error || "Gagal generate caption", "error");
  }
}

// ── Regenerate schedule ──
async function regenSchedule() {
  try {
    const res = await API.post("/api/upload/regen-schedule", {
      count: Upload.session.videos.length,
    });
    if (res.schedule) {
      Upload.session.schedule = res.schedule;
      renderWorkflow();
      toast("Jadwal diperbarui", "success", 1500);
    }
  } catch (err) {
    toast(err.error || "Gagal generate jadwal", "error");
  }
}
