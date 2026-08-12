const $ = (id) => document.getElementById(id);

const hSelect = $("hSelect");
const vSelect = $("vSelect");
const storagePath = $("storagePath");
const btnBrowseStorage = $("btnBrowseStorage");
const btnApplyStorage = $("btnApplyStorage");
const btnResetStorage = $("btnResetStorage");

// Storage Modal UI elements
const storageModal = $("storageModal");
const closeStorageModal = $("closeStorageModal");
const storageFolderList = $("storageFolderList");
const currentStoragePath = $("currentStoragePath");
const btnStorageUp = $("btnStorageUp");
const btnSelectStorageFolder = $("btnSelectStorageFolder");
const btnCancelStorageModal = $("btnCancelStorageModal");
const sec2 = $("sec2");
const sec5 = $("sec5");
const gridOuter = $("gridOuter");
const gridWrap = document.querySelector(".gridWrap");
const gridFilledCount = $("gridFilledCount");
const gridTotalCount = $("gridTotalCount");
const gridProgressFill = $("gridProgressFill");
const cellInspector = $("cellInspector");
const inspectorCellLabel = $("inspectorCellLabel");
const inspectorFileName = $("inspectorFileName");
const inspectorStatus = $("inspectorStatus");
const btnInspectorUpload = $("btnInspectorUpload");
const topMatrixSummary = $("topMatrixSummary");
const btnGoRender = $("btnGoRender");
const setupGridSize = $("setupGridSize");
const setupTotalCells = $("setupTotalCells");
const setupFilledCells = $("setupFilledCells");
const setupClipsPerOutput = $("setupClipsPerOutput");
const setupCalcState = $("setupCalcState");
const setupEstimateGridLabel = $("setupEstimateGridLabel");
const renderMatrixSummary = $("renderMatrixSummary");
const renderFilledSummary = $("renderFilledSummary");
const renderClipSummary = $("renderClipSummary");
const renderCalcSummary = $("renderCalcSummary");
const storageSummaryPath = $("storageSummaryPath");
const workflowTabs = Array.from(document.querySelectorAll("[data-tab-target]"));
const workflowPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const massUploadHint = $("massUploadHint");
const gridHint = $("gridHint");
const btnGenerate = $("btnGenerate");
const btnStop = $("btnStop");
const progressWrap = $("progressWrap");
const perModeProgress = $("perModeProgress");
const globalLine = $("globalLine");
const logEl = $("log");

const mHorizontal = $("mHorizontal");
const mMixHorizontal = $("mMixHorizontal");
const mMixHorizontalLinear = $("mMixHorizontalLinear");
const mMixHorizontalLinearUnique = $("mMixHorizontalLinearUnique");

const batchNone = $("batchNone");
const batchLimit = $("batchLimit");
const largeOutputModal = $("largeOutputModal");
const largeOutputCount = $("largeOutputCount");
const largeOutputThreshold = $("largeOutputThreshold");
const largeOutputGrid = $("largeOutputGrid");
const largeOutputModes = $("largeOutputModes");
const btnReviewLargeOutput = $("btnReviewLargeOutput");
const btnConfirmLargeOutput = $("btnConfirmLargeOutput");
let pendingLargeOutput = null;
const batchSize = $("batchSize");
const folderPolicy = $("folderPolicy");
const folderPolicyCustom = $("folderPolicyCustom");
const folderPolicyCustomWrap = $("folderPolicyCustomWrap");

// Tampilkan input manual hanya saat opsi "custom" dipilih.
function _syncFolderPolicyCustom() {
  if (!folderPolicy || !folderPolicyCustomWrap) return;
  const isCustom = folderPolicy.value === "custom";
  folderPolicyCustomWrap.style.display = isCustom ? "" : "none";
}
if (folderPolicy) {
  folderPolicy.addEventListener("change", _syncFolderPolicyCustom);
  _syncFolderPolicyCustom();
}

// Resolusi nilai folderPolicy final yang dikirim ke backend.
// - "all"            -> satu folder
// - angka (4/5/24)   -> wrap per N
// - "custom" + input -> wrap per N manual (fallback "all" jika kosong/invalid)
function resolveFolderPolicy() {
  if (!folderPolicy) return "all";
  const v = String(folderPolicy.value || "all");
  if (v !== "custom") return v;
  const raw = folderPolicyCustom ? parseInt(folderPolicyCustom.value, 10) : NaN;
  if (Number.isFinite(raw) && raw >= 1) return String(raw);
  return "all";
}
// v1.9: mode audio (mute | keep | replace | mix) menggantikan checkbox
// muteAudio tunggal. Radio group "audioMode".
const audioModeRadios = Array.from(document.querySelectorAll('input[name="audioMode"]'));
const audioUploadPanel = $("audioUploadPanel");
const audioFileInput = $("audioFileInput");
const audioUploadStatus = $("audioUploadStatus");
const audioCountBadge = $("audioCountBadge");
const btnAudioViewList = $("btnAudioViewList");
const btnAudioClearAll = $("btnAudioClearAll");
const audioListModal = $("audioListModal");
const audioListBody = $("audioListBody");
const closeAudioListModal = $("closeAudioListModal");
const btnCloseAudioListModal = $("btnCloseAudioListModal");

function getAudioMode() {
  const checked = audioModeRadios.find((r) => r.checked);
  return checked ? checked.value : "mute";
}
function audioModeNeedsFiles() {
  const m = getAudioMode();
  return m === "replace" || m === "mix";
}

// v1.1.2: pilihan encoder video (auto | nvenc | vaapi | cpu).
// Dikirim sebagai `encoderMode` di payload /api/start; backend fallback ke
// "auto" bila tidak ada (kompatibel mundur).
const encoderMode = $("encoderMode");

// v1.5 FIX: panel "Performa" (v1.4) tidak pernah dibaca oleh app.js sehingga
// pilihan Metode render & Worker paralel tidak pernah dikirim ke backend
// (backend selalu memakai default). Kini dibaca dan dikirim di /api/start.
const renderMethod = $("renderMethod");
const parallelWorkers = $("parallelWorkers");

// v1.6: kontrol Kualitas output (resolusi / fps / kualitas / bitrate).
// Default disetel setara sumber 720p @24fps agar tidak boros waktu & ukuran.
const qualityPreset = $("qualityPreset");
const resPreset = $("resPreset");
const resCustomWrap = $("resCustomWrap");
const resCustomW = $("resCustomW");
const resCustomH = $("resCustomH");
const fpsSelect = $("fpsSelect");
const rateMode = $("rateMode");
const qualityWrap = $("qualityWrap");
const qualitySelect = $("qualitySelect");
const videoBitrateWrap = $("videoBitrateWrap");
const videoBitrateK = $("videoBitrateK");
const audioBitrateWrap = $("audioBitrateWrap");
const audioBitrateK = $("audioBitrateK");
const qualityHint = $("qualityHint");
const footerProfile = $("footerProfile");

// Preset cepat → nilai kontrol detail. Preset hanya "menulis" ke kontrol;
// kontrol detail tetap sumber kebenaran yang dikirim ke backend.
const QUALITY_PRESETS = {
  source720:    { res: "720x1280",  fps: "24", rateMode: "crf", quality: "23" },
  balanced1080: { res: "1080x1920", fps: "30", rateMode: "crf", quality: "23" },
  max1080:      { res: "1080x1920", fps: "30", rateMode: "crf", quality: "20" },
};

// Set nilai <select>; jika value tidak ada di opsi (mis. resolusi kustom),
// biarkan apa adanya agar tidak menimpa pilihan user.
function _setSelect(sel, value) {
  if (!sel) return;
  const has = Array.from(sel.options).some((o) => o.value === value);
  if (has) sel.value = value;
}

function applyQualityPreset() {
  if (!qualityPreset) return;
  const key = qualityPreset.value;
  if (key === "custom") { syncOutputProfileUI(); return; }
  const p = QUALITY_PRESETS[key];
  if (!p) { syncOutputProfileUI(); return; }
  _setSelect(resPreset, p.res);
  _setSelect(fpsSelect, p.fps);
  _setSelect(rateMode, p.rateMode);
  _setSelect(qualitySelect, p.quality);
  syncOutputProfileUI();
}

// Tampilkan/sembunyikan kontrol yang relevan + perbarui footer + reset estimasi.
function syncOutputProfileUI() {
  if (resCustomWrap) resCustomWrap.style.display = (resPreset && resPreset.value === "custom") ? "" : "none";

  const isBitrate = rateMode && rateMode.value === "bitrate";
  if (qualityWrap) qualityWrap.style.display = isBitrate ? "none" : "";
  if (videoBitrateWrap) videoBitrateWrap.style.display = isBitrate ? "" : "none";

  const audioOn = getAudioMode() !== "mute";
  if (audioBitrateWrap) audioBitrateWrap.style.display = audioOn ? "" : "none";

  updateFooterProfile();
  resetSizeEstimate();
}

// Saat user mengubah kontrol detail secara manual, preset jadi "Kustom".
function markPresetCustom() {
  if (qualityPreset) qualityPreset.value = "custom";
  syncOutputProfileUI();
}

// ── Audio eksternal (v1.9): Replace/Mix, upload 1-n file, rolling round-robin ──

function syncAudioModeUI() {
  const needsFiles = audioModeNeedsFiles();
  if (audioUploadPanel) audioUploadPanel.style.display = needsFiles ? "" : "none";
}

function updateAudioSummaryUI() {
  const n = state.audioFiles.length;
  if (audioCountBadge) audioCountBadge.textContent = `🎵 ${n.toLocaleString("id-ID")} file audio ter-upload`;
  if (btnAudioViewList) btnAudioViewList.disabled = n === 0;
  if (btnAudioClearAll) btnAudioClearAll.disabled = n === 0;
}

async function loadAudioList() {
  try {
    const resp = await fetch("/api/audio_list");
    const json = await resp.json();
    if (json.ok) {
      state.audioFiles = json.items || [];
      updateAudioSummaryUI();
    }
  } catch (e) {
    // Diam-diam gagal; panel audio tetap menampilkan state terakhir yang diketahui.
  }
}

async function uploadAudioFiles(files) {
  const queue = Array.from(files || []);
  if (!queue.length) return;

  if (audioFileInput) audioFileInput.disabled = true;
  if (audioUploadStatus) {
    audioUploadStatus.classList.remove("success", "error");
    audioUploadStatus.classList.add("uploading");
    audioUploadStatus.textContent = `Mengunggah 0/${queue.length} file...`;
  }

  let okCount = 0;
  let failCount = 0;

  try {
    for (let i = 0; i < queue.length; i++) {
      if (audioUploadStatus) {
        audioUploadStatus.textContent = `Mengunggah ${i + 1}/${queue.length}: ${queue[i].name}`;
      }
      const fd = new FormData();
      fd.append("file", queue[i]);
      try {
        const resp = await fetch("/api/upload_audio", { method: "POST", body: fd });
        const json = await resp.json();
        if (json.ok) okCount++; else failCount++;
      } catch (e) {
        failCount++;
      }
    }
  } finally {
    if (audioFileInput) {
      audioFileInput.disabled = false;
      audioFileInput.value = "";
    }
  }

  await loadAudioList();
  await loadStorageUsage();

  if (audioUploadStatus) {
    audioUploadStatus.classList.remove("uploading");
    audioUploadStatus.classList.toggle("success", failCount === 0);
    audioUploadStatus.classList.toggle("error", failCount > 0);
    audioUploadStatus.textContent = failCount > 0
      ? `${okCount} file berhasil, ${failCount} gagal diunggah.`
      : `${okCount} file berhasil diunggah otomatis.`;
  }
  if (failCount > 0 && logEl) {
    logEl.textContent = `Upload audio: ${okCount} berhasil, ${failCount} gagal.`;
  }
}

function renderAudioListModal() {
  if (!audioListBody) return;
  audioListBody.innerHTML = "";
  if (!state.audioFiles.length) {
    audioListBody.innerHTML = '<p class="hint" style="padding:10px">Belum ada file audio ter-upload.</p>';
    return;
  }
  state.audioFiles.forEach((item, idx) => {
    const row = document.createElement("div");
    row.className = "folder-item";
    row.style.display = "flex";
    row.style.alignItems = "center";
    row.style.justifyContent = "space-between";
    row.style.gap = "8px";

    const label = document.createElement("span");
    label.className = "mono";
    label.style.overflow = "hidden";
    label.style.textOverflow = "ellipsis";
    label.style.whiteSpace = "nowrap";
    label.textContent = `${idx + 1}. ${item.filename}`;
    label.title = item.filename;

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn sm danger";
    delBtn.textContent = "Hapus";
    delBtn.addEventListener("click", async () => {
      delBtn.disabled = true;
      delBtn.textContent = "...";
      await deleteAudioFile(item.path);
      renderAudioListModal();
    });

    row.appendChild(label);
    row.appendChild(delBtn);
    audioListBody.appendChild(row);
  });
}

async function deleteAudioFile(path) {
  try {
    await fetch("/api/audio_delete", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
  } catch (e) {
    // abaikan; loadAudioList akan mengoreksi state di panggilan berikutnya
  }
  await loadAudioList();
  await loadStorageUsage();
}

async function clearAllAudio() {
  if (!confirm(`Hapus semua ${state.audioFiles.length} file audio yang sudah diupload? Tindakan ini tidak dapat dibatalkan.`)) return;
  try {
    await fetch("/api/audio_clear", { method: "DELETE" });
  } catch (e) {
    // abaikan
  }
  await loadAudioList();
  await loadStorageUsage();
}

function openAudioListModal() {
  renderAudioListModal();
  if (audioListModal) audioListModal.style.display = "flex";
}
function closeAudioListModalFn() {
  if (audioListModal) audioListModal.style.display = "none";
}

if (audioFileInput) {
  audioFileInput.addEventListener("change", async () => {
    const files = Array.from(audioFileInput.files || []);
    if (files.length) await uploadAudioFiles(files);
  });
}
if (btnAudioViewList) btnAudioViewList.addEventListener("click", openAudioListModal);
if (btnAudioClearAll) btnAudioClearAll.addEventListener("click", clearAllAudio);
if (closeAudioListModal) closeAudioListModal.addEventListener("click", closeAudioListModalFn);
if (btnCloseAudioListModal) btnCloseAudioListModal.addEventListener("click", closeAudioListModalFn);
window.addEventListener("click", (event) => {
  if (audioListModal && event.target === audioListModal) closeAudioListModalFn();
});

function _resolveResolution() {
  const v = resPreset ? String(resPreset.value || "720x1280") : "720x1280";
  if (v !== "custom") {
    const [w, h] = v.split("x").map((n) => parseInt(n, 10));
    return { width: w || 720, height: h || 1280 };
  }
  let w = resCustomW ? parseInt(resCustomW.value, 10) : NaN;
  let h = resCustomH ? parseInt(resCustomH.value, 10) : NaN;
  if (!Number.isFinite(w) || w < 16) w = 720;
  if (!Number.isFinite(h) || h < 16) h = 1280;
  // Dimensi H.264 yuv420p wajib genap (backend juga meng-clamp).
  if (w % 2) w -= 1;
  if (h % 2) h -= 1;
  return { width: w, height: h };
}

// Objek profil output yang dikirim ke backend (dibaca oleh /api/start dan
// /api/estimate_size). Backend memvalidasi & meng-clamp ulang semua nilai.
function readOutputProfile() {
  const { width, height } = _resolveResolution();
  const fps = fpsSelect ? parseInt(fpsSelect.value, 10) || 24 : 24;
  const rm = rateMode ? String(rateMode.value || "crf") : "crf";
  const quality = qualitySelect ? parseInt(qualitySelect.value, 10) : 23;
  const vbk = videoBitrateK ? parseInt(videoBitrateK.value, 10) : 2000;
  const abk = audioBitrateK ? parseInt(audioBitrateK.value, 10) : 128;
  return {
    width, height, fps,
    rateMode: rm === "bitrate" ? "bitrate" : "crf",
    quality: Number.isFinite(quality) ? quality : 23,
    videoBitrateK: Number.isFinite(vbk) && vbk > 0 ? vbk : 2000,
    audioBitrateK: Number.isFinite(abk) && abk > 0 ? abk : 128,
  };
}

function updateFooterProfile() {
  if (!footerProfile) return;
  const p = readOutputProfile();
  footerProfile.textContent = `${p.width}×${p.height} @${p.fps}fps`;
}

// v1.5 FIX: elemen status v1.4 yang belum pernah dihubungkan ke JS.
const sysChip = $("sysChip");               // chip info sistem di topbar
const encoderDetected = $("encoderDetected"); // hint encoder di Panel 5
const phaseChip = $("phaseChip");           // chip tahap (normalisasi/render)
const globalBarFill = $("globalBarFill");   // bar progres global besar
const outDirLine = $("outDirLine");         // baris lokasi folder output

// Estimasi ukuran output (v1.1)
const sizeEstimate = $("sizeEstimate");
const sizeEstimateBody = $("sizeEstimateBody");
const btnEstimateSize = $("btnEstimateSize");

// Storage Usage selectors
const usageUploadsSize = $("usageUploadsSize");
const usageUploadsCount = $("usageUploadsCount");
const usageOutputsSize = $("usageOutputsSize");
const usageOutputsCount = $("usageOutputsCount");
const usageTempSize = $("usageTempSize");
const usageTempCount = $("usageTempCount");
const usageAudioSize = $("usageAudioSize");
const usageAudioCount = $("usageAudioCount");
const btnRefreshUsage = $("btnRefreshUsage");
const btnCleanUploads = $("btnCleanUploads");
const btnCleanOutputs = $("btnCleanOutputs");
const btnCleanAudio = $("btnCleanAudio");
const btnCleanAll = $("btnCleanAll");


let state = {
  // IMPORTANT: mengikuti request user
  // h = Horizontal = jumlah kolom
  // v = Vertical   = jumlah baris
  h: 0,
  v: 0,
  grid: [], // [row][col] = { label, path, filename }
  estimates: null,
  locked: false,
  storageBase: null,
  currentJobId: null,   // v1.1: job yang sedang berjalan (untuk tombol Stop)
  stopping: false,      // v1.1: true saat permintaan Stop sedang diproses
  audioFiles: [],        // v1.9: [{ path, filename, sizeBytes }] hasil upload audio
  activeWorkspaceTab: "setup", // v1.16: hanya Setup dan Render
  selectedCell: null,           // v1.16: { r, c } untuk panel detail sel
};

function syncBatchUI() {
  const limited = batchLimit.checked;
  batchSize.disabled = !limited;
  if (!limited) batchSize.value = "";
  if (limited && !batchSize.value) batchSize.value = "100";
  const safety = $("batchSafetyHint");
  if (safety) {
    safety.classList.toggle("warn", !limited);
    safety.textContent = limited
      ? "Limit aktif untuk mencegah produksi file berlebihan. Nilai berlaku per mode yang dipilih."
      : "Tanpa limit tetap aktif. Jika hasil melebihi 30.000 video, aplikasi akan meminta konfirmasi sebelum render dimulai.";
  }
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

async function loadStorageUsage() {
  try {
    const resp = await fetch("/api/storage/usage");
    const json = await resp.json();
    if (json.ok) {
      if (usageUploadsSize) usageUploadsSize.textContent = formatBytes(json.uploads.sizeBytes);
      if (usageUploadsCount) usageUploadsCount.textContent = json.uploads.count;
      
      if (usageOutputsSize) usageOutputsSize.textContent = formatBytes(json.outputs.sizeBytes);
      if (usageOutputsCount) usageOutputsCount.textContent = json.outputs.count;
      
      if (usageTempSize) usageTempSize.textContent = formatBytes(json.temp.sizeBytes);
      if (usageTempCount) usageTempCount.textContent = json.temp.count;

      if (json.audio) {
        if (usageAudioSize) usageAudioSize.textContent = formatBytes(json.audio.sizeBytes);
        if (usageAudioCount) usageAudioCount.textContent = json.audio.count;
      }
    }
  } catch (e) {
    console.error("Gagal memuat info storage:", e);
  }
}

async function cleanStorage(targets) {
  try {
    const resp = await fetch("/api/storage/clean", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ targets })
    });
    const json = await resp.json();
    if (!json.ok) throw new Error(json.error || "clean_failed");
    logEl.textContent = `Berhasil membersihkan: ${json.cleaned.join(", ")}`;
    await loadStorageUsage();
  } catch (e) {
    logEl.textContent = `Gagal membersihkan storage: ${e.message}`;
  }
}

// v1.5 FIX: endpoint /api/system (v1.4) tidak pernah dipanggil, sehingga chip
// "memeriksa sistem…" di topbar tidak pernah berubah dan hint encoder di
// Panel 5 tidak menampilkan hasil deteksi. Panggilan pertama bisa 1–2 detik
// (server melakukan test encode, hasilnya di-cache).
async function loadSystemInfo() {
  if (!sysChip && !encoderDetected) return;
  try {
    const resp = await fetch("/api/system");
    const json = await resp.json();
    if (!json.ok) throw new Error("system_info_failed");

    const enc = json.encoder || {};
    const encLabel =
      enc.mode === "nvenc" ? `GPU NVENC — ${enc.label || "NVIDIA"}` :
      enc.mode === "vaapi" ? `GPU VAAPI — ${enc.label || "AMD/Intel"}` :
      `CPU — ${enc.label || "libx264"}`;

    if (sysChip) {
      sysChip.textContent = `${encLabel} · ${json.cpuThreads} thread · auto ${json.autoWorkers} worker`;
      sysChip.title = json.ffmpeg || "";
    }
    if (encoderDetected) {
      let hint = `Terdeteksi: ${encLabel}.`;
      if (enc.mode === "cpu" && enc.reason) hint += ` (${enc.reason})`;
      hint += " Auto memakai GPU bila terdeteksi dan otomatis fallback ke CPU. Encoder aktif tercatat di log.";
      encoderDetected.textContent = hint;
    }
  } catch (e) {
    if (sysChip) sysChip.textContent = "info sistem tidak tersedia";
  }
}

async function loadStorageBase() {
  try {
    const resp = await fetch("/api/storage");
    const json = await resp.json();
    if (json.ok) {
      state.storageBase = json.storageBase;
      if (storagePath) storagePath.value = json.storageBase;
      if (storageSummaryPath) storageSummaryPath.textContent = json.storageBase;
      await loadStorageUsage();
    }
  } catch {
    // ignore
  }
}

async function setStorageBase(path) {
  const resp = await fetch("/api/storage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: path ?? "" }),
  });
  const json = await resp.json();
  if (!json.ok) throw new Error(json.error || "storage_set_failed");
  state.storageBase = json.storageBase;
  if (storagePath) storagePath.value = json.storageBase;
  if (storageSummaryPath) storageSummaryPath.textContent = json.storageBase;
}

let modalCurrentPath = "";
let modalSelectedPath = "";

function closeStorageModalFn() {
  if (storageModal) storageModal.style.display = "none";
}

async function loadModalDirectory(path) {
  if (!storageFolderList) return;
  try {
    storageFolderList.innerHTML = "<div class='modal-loading'>Loading folders...</div>";
    const url = `/api/storage/list_dirs?path=${encodeURIComponent(path)}`;
    const resp = await fetch(url);
    const json = await resp.json();
    if (!json.ok) {
      storageFolderList.innerHTML = `<div class='modal-error'>Gagal memuat folder: ${json.error}</div>`;
      return;
    }

    modalCurrentPath = json.currentPath;
    modalSelectedPath = json.currentPath;
    if (currentStoragePath) currentStoragePath.textContent = json.currentPath;
    
    if (btnStorageUp) {
      if (json.parentPath) {
        btnStorageUp.disabled = false;
        btnStorageUp.dataset.parent = json.parentPath;
      } else {
        btnStorageUp.disabled = true;
        btnStorageUp.dataset.parent = "";
      }
    }

    storageFolderList.innerHTML = "";
    if (json.subdirs.length === 0) {
      storageFolderList.innerHTML = "<div class='modal-empty'>Tidak ada subfolder</div>";
      return;
    }

    json.subdirs.forEach(dir => {
      const el = document.createElement("div");
      el.className = "folder-item";
      
      const icon = document.createElement("span");
      icon.className = "folder-icon";
      icon.innerHTML = "&#128193;";
      
      const name = document.createElement("span");
      name.className = "folder-name";
      name.textContent = dir.name;
      
      el.appendChild(icon);
      el.appendChild(name);
      
      el.addEventListener("click", () => {
        document.querySelectorAll(".folder-item").forEach(item => item.classList.remove("selected"));
        el.classList.add("selected");
        modalSelectedPath = dir.path;
      });
      
      el.addEventListener("dblclick", () => {
        loadModalDirectory(dir.path);
      });
      
      storageFolderList.appendChild(el);
    });
  } catch (e) {
    storageFolderList.innerHTML = `<div class='modal-error'>Eror: ${e.message}</div>`;
  }
}

function openStorageModal() {
  if (storageModal) {
    storageModal.style.display = "flex";
    loadModalDirectory(state.storageBase || "");
  }
}



// ── UI workspace v1.16: two-step workflow, fixed matrix, progress, inspector ──
function _tabAvailability() {
  return {
    setup: true,
    render: !!sec5 && !sec5.classList.contains("disabled"),
  };
}

function openWorkspaceTab(name, force = false) {
  const availability = _tabAvailability();
  if (!force && !availability[name]) return false;

  state.activeWorkspaceTab = name;
  workflowTabs.forEach((tab) => {
    const active = tab.dataset.tabTarget === name;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", active ? "true" : "false");
    const stateEl = tab.querySelector(".workflow-tab-state");
    if (stateEl) {
      if (active) stateEl.textContent = "Aktif";
      else if (tab.disabled) stateEl.textContent = "Terkunci";
      else if (tab.classList.contains("complete")) stateEl.textContent = "Selesai";
      else stateEl.textContent = "Siap";
    }
  });
  workflowPanels.forEach((panel) => {
    const active = panel.dataset.tabPanel === name;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });

  if (name === "setup") requestAnimationFrame(applyGridLayout);
  return true;
}

function syncWorkflowTabs() {
  const availability = _tabAvailability();
  const completed = {
    setup: isGridComplete() && !!state.estimates,
    render: false,
  };

  workflowTabs.forEach((tab) => {
    const name = tab.dataset.tabTarget;
    tab.disabled = !availability[name];
    tab.classList.toggle("complete", !!completed[name]);
    const stateEl = tab.querySelector(".workflow-tab-state");
    if (!stateEl) return;
    if (state.activeWorkspaceTab === name) stateEl.textContent = "Aktif";
    else if (!availability[name]) stateEl.textContent = "Terkunci";
    else if (completed[name]) stateEl.textContent = "Selesai";
    else stateEl.textContent = "Siap";
  });

  if (!availability[state.activeWorkspaceTab]) {
    openWorkspaceTab("setup", true);
  } else {
    openWorkspaceTab(state.activeWorkspaceTab, true);
  }
}

function countFilledCells() {
  let filled = 0;
  for (const row of state.grid) {
    for (const cell of row) if (cell.path) filled++;
  }
  return filled;
}

function updateWorkspaceSummaries() {
  const ready = state.h > 0 && state.v > 0;
  const total = ready ? state.h * state.v : 0;
  const filled = countFilledCells();
  const matrix = ready ? `${state.h} × ${state.v}` : "—";
  const filledText = `${filled.toLocaleString("id-ID")} / ${total.toLocaleString("id-ID")}`;
  const clips = ready ? String(state.h) : "—";

  if (topMatrixSummary) {
    topMatrixSummary.textContent = ready
      ? `${matrix} · ${total.toLocaleString("id-ID")} sel · ${filled.toLocaleString("id-ID")} terisi`
      : "Matriks belum disetel";
  }
  if (setupGridSize) setupGridSize.textContent = matrix;
  if (setupTotalCells) setupTotalCells.textContent = total.toLocaleString("id-ID");
  if (setupFilledCells) setupFilledCells.textContent = filledText;
  if (setupClipsPerOutput) setupClipsPerOutput.textContent = clips;
  if (setupEstimateGridLabel) setupEstimateGridLabel.textContent = ready ? `Grid ${matrix}` : "Pilih grid";
  if (renderMatrixSummary) renderMatrixSummary.textContent = matrix;
  if (renderFilledSummary) renderFilledSummary.textContent = filledText;
  if (renderClipSummary) renderClipSummary.textContent = clips;
}

function updateMatrixSummary() {
  updateWorkspaceSummaries();
}

function updateGridSummary() {
  const total = state.h && state.v ? state.h * state.v : 0;
  const filled = countFilledCells();
  if (gridFilledCount) gridFilledCount.textContent = filled.toLocaleString("id-ID");
  if (gridTotalCount) gridTotalCount.textContent = total.toLocaleString("id-ID");
  if (gridProgressFill) gridProgressFill.style.width = `${total ? (filled / total) * 100 : 0}%`;
  updateWorkspaceSummaries();
}

function setCalcStatus(text, kind = "idle") {
  [setupCalcState, renderCalcSummary].forEach((el) => {
    if (!el) return;
    el.textContent = text;
    el.dataset.state = kind;
  });
}

function clearCellInspector() {
  state.selectedCell = null;
  document.querySelectorAll("#gridOuter .cell.selected").forEach((el) => el.classList.remove("selected"));
  if (cellInspector) cellInspector.hidden = true;
}

function syncCellInspector() {
  if (!cellInspector || !state.selectedCell) return;
  const { r, c } = state.selectedCell;
  const data = state.grid?.[r]?.[c];
  if (!data) {
    clearCellInspector();
    return;
  }
  cellInspector.hidden = false;
  if (inspectorCellLabel) inspectorCellLabel.textContent = data.label;
  if (inspectorFileName) inspectorFileName.textContent = data.filename || "Belum ada file";
  if (inspectorStatus) {
    inspectorStatus.textContent = data.uploading ? "Mengunggah" : data.error ? "Gagal" : data.path ? "Terunggah" : "Kosong";
  }
  if (btnInspectorUpload) btnInspectorUpload.textContent = data.path ? "Ganti video" : "Pilih video";
}

function selectGridCell(r, c) {
  state.selectedCell = { r, c };
  document.querySelectorAll("#gridOuter .cell.selected").forEach((el) => el.classList.remove("selected"));
  const cell = $(`cell_${r}_${c}`);
  if (cell) cell.classList.add("selected");
  syncCellInspector();
}

function applyGridLayout() {
  if (!gridOuter || !gridWrap || !state.h) return;
  // v1.15: matriks maksimum 10 kolom selalu memakai seluruh lebar panel.
  // Tidak ada area scroll internal; seluruh baris mengikuti tinggi konten.
  const columns = Math.max(1, Number(state.h) || 1);
  const available = Math.max(280, gridWrap.clientWidth - 8);
  const headW = columns >= 9 ? 38 : 44;
  const gap = columns >= 9 ? 3 : 4;
  const estimatedCellW = (available - headW - (gap * columns) - 8) / columns;
  gridOuter.dataset.view = "fixed";
  gridOuter.style.setProperty("--grid-gap", `${gap}px`);
  gridOuter.style.gridTemplateColumns = `${headW}px repeat(${columns}, minmax(0, 1fr))`;
  gridOuter.classList.toggle("micro", estimatedCellW < 82);
}

let _gridResizeTimer = null;
function scheduleGridLayout() {
  clearTimeout(_gridResizeTimer);
  _gridResizeTimer = setTimeout(applyGridLayout, 80);
}

function fillSelect(sel) {
  // Range pilihan matriks dibatasi 1–10.
  for (let i = 1; i <= 10; i++) {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = String(i);
    sel.appendChild(opt);
  }
}

fillSelect(hSelect);
fillSelect(vSelect);

function setEnabled(sectionEl, enabled) {
  if (!sectionEl) return;
  sectionEl.classList.toggle("disabled", !enabled);
  syncWorkflowTabs();
}

function resetModeEstimateUI() {
  const modeIds = {
    horizontal: { render: "maxHorizontal", setup: "setupMaxHorizontal" },
    mixHorizontal: { render: "maxMixHorizontal", setup: "setupMaxMixHorizontal" },
    mixHorizontalLinear: { render: "maxMixHorizontalLinear", setup: "setupMaxMixHorizontalLinear" },
    mixHorizontalLinearUnique: { render: "maxMixHorizontalLinearUnique", setup: "setupMaxMixHorizontalLinearUnique" },
  };
  Object.entries(modeIds).forEach(([key, ids]) => {
    [$(ids.render), $(ids.setup)].forEach((maxEl) => {
      if (maxEl) maxEl.textContent = "—";
    });

    const renderValidity = document.querySelector(`[data-mode-validity="${key}"]`);
    const renderCard = document.querySelector(`[data-mode-card="${key}"]`);
    if (renderValidity) {
      renderValidity.textContent = "Menunggu kalkulasi";
      renderValidity.className = "mode-validity";
    }
    if (renderCard) renderCard.classList.remove("valid", "invalid");

    const setupValidity = document.querySelector(`[data-setup-validity="${key}"]`);
    const setupCard = document.querySelector(`[data-setup-estimate-card="${key}"]`);
    if (setupValidity) {
      setupValidity.textContent = "Menunggu grid";
      setupValidity.className = "setup-mode-validity";
    }
    if (setupCard) setupCard.classList.remove("valid", "invalid");
  });
}

function resetBelow(level) {
  // level 1: ukuran matriks berubah; level 2: isi grid berubah.
  if (level <= 1) {
    state.grid = [];
    state.estimates = null;
    gridOuter.innerHTML = "";
    if (massUploadHint) { massUploadHint.textContent = ""; massUploadHint.style.display = "none"; }
    [mHorizontal, mMixHorizontal, mMixHorizontalLinear, mMixHorizontalLinearUnique].forEach((c) => {
      c.checked = false;
      c.disabled = false;
      c.dataset.invalid = "0";
    });
    resetModeEstimateUI();
    setCalcStatus("Menunggu grid", "idle");
    btnGenerate.disabled = true;
    if (btnGoRender) btnGoRender.disabled = true;
    progressWrap.hidden = true;
    perModeProgress.innerHTML = "";
    globalLine.textContent = "";
    logEl.textContent = "";
  }
  if (level <= 2) {
    // Kalkulasi kombinasi bergantung hanya pada H×V, jadi tidak dihapus saat
    // file pada sel berubah. Hanya estimasi ukuran/render lama yang direset.
    btnGenerate.disabled = true;
    progressWrap.hidden = true;
    resetSizeEstimate();
  }
  if (level <= 1) clearCellInspector();
  updateGridSummary();
  updateMatrixSummary();
  syncWorkflowTabs();
}

function updateOutputStructure() {
  // Panjang setiap output untuk seluruh keluarga mode horizontal = H.
  // Nilainya kini ditampilkan sebagai ringkasan, bukan langkah terpisah.
  updateWorkspaceSummaries();
}

function buildGrid() {
  // grid = V baris x H kolom; struktur data dan label engine tetap sama.
  const h = state.h;
  const v = state.v;

  state.grid = Array.from({ length: v }, (_, r) =>
    Array.from({ length: h }, (_, c) => ({
      label: `${String.fromCharCode(65 + r)}${c + 1}`,
      path: null,
      filename: null,
      uploading: false,
      error: null,
    }))
  );

  clearCellInspector();
  gridOuter.innerHTML = "";
  const rowColors = ["#6e8bff", "#7898ef", "#6686da", "#8298d7"];

  const corner = document.createElement("div");
  corner.className = "gridHeadCell gridCorner";
  corner.title = "Upload massal tersedia pada setiap header baris dan kolom";
  gridOuter.appendChild(corner);

  for (let c = 0; c < h; c++) {
    gridOuter.appendChild(buildMassUploadHeader("col", c, `${c + 1}`, null));
  }

  for (let r = 0; r < v; r++) {
    const rowColor = rowColors[r % rowColors.length];
    const rowLabel = String.fromCharCode(65 + r);
    gridOuter.appendChild(buildMassUploadHeader("row", r, rowLabel, rowColor));

    for (let c = 0; c < h; c++) {
      const cellData = state.grid[r][c];
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.id = `cell_${r}_${c}`;
      cell.style.setProperty("--row-color", rowColor);
      cell.tabIndex = 0;
      cell.setAttribute("role", "button");
      cell.setAttribute("aria-label", `${cellData.label}, belum diisi`);
      cell.title = `${cellData.label} — klik untuk detail, klik dua kali untuk upload`;

      const label = document.createElement("div");
      label.className = "label";
      label.textContent = cellData.label;

      const dropzone = document.createElement("div");
      dropzone.className = "dropzone";

      const icon = document.createElement("span");
      icon.className = "icon";
      icon.textContent = "+";
      icon.id = `icon_${r}_${c}`;

      const text = document.createElement("span");
      text.className = "text";
      text.textContent = "Kosong";
      text.id = `text_${r}_${c}`;

      dropzone.appendChild(icon);
      dropzone.appendChild(text);

      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "cell-upload-trigger";
      trigger.textContent = "+";
      trigger.title = `Pilih video untuk ${cellData.label}`;
      trigger.setAttribute("aria-label", `Pilih video untuk ${cellData.label}`);

      const input = document.createElement("input");
      input.type = "file";
      input.accept = "video/*";
      input.id = `input_${r}_${c}`;
      input.className = "cell-file-input";

      const status = document.createElement("div");
      status.className = "status";
      status.id = `status_${r}_${c}`;
      status.textContent = "Belum diisi";

      cell.addEventListener("click", () => selectGridCell(r, c));
      cell.addEventListener("dblclick", (event) => {
        event.preventDefault();
        if (!state.locked) input.click();
      });
      cell.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectGridCell(r, c);
        }
      });
      trigger.addEventListener("click", (event) => {
        event.stopPropagation();
        if (state.locked) return;
        selectGridCell(r, c);
        input.value = "";
        input.click();
      });
      cell.addEventListener("dragenter", (event) => {
        event.preventDefault();
        cell.classList.add("drag-over");
      });
      cell.addEventListener("dragover", (event) => {
        event.preventDefault();
        cell.classList.add("drag-over");
      });
      cell.addEventListener("dragleave", () => cell.classList.remove("drag-over"));
      cell.addEventListener("drop", async (event) => {
        event.preventDefault();
        cell.classList.remove("drag-over");
        if (state.locked) return;
        const file = event.dataTransfer?.files?.[0];
        if (!file) return;
        selectGridCell(r, c);
        await uploadCell(r, c, file);
      });
      input.addEventListener("change", async () => {
        if (!input.files || !input.files[0]) return;
        selectGridCell(r, c);
        await uploadCell(r, c, input.files[0]);
      });

      cell.appendChild(label);
      cell.appendChild(dropzone);
      cell.appendChild(trigger);
      cell.appendChild(input);
      cell.appendChild(status);
      gridOuter.appendChild(cell);
    }
  }

  updateGridSummary();
  requestAnimationFrame(applyGridLayout);
  updateGridValidity();
}

// ── Upload massal per baris/kolom ──
// Header ini tampil di baris 0 (per kolom) dan kolom 0 (per baris) pada
// #gridOuter. Klik header -> buka dialog multi-select file -> isi sel-sel
// baris/kolom tsb secara berurutan sesuai urutan file yang diterima
// browser. Kelebihan file di-skip (+ hint), kekurangan dibiarkan kosong
// untuk diisi manual (klik sel satu-satu seperti biasa).
function buildMassUploadHeader(kind, index, labelText, rowColor) {
  const head = document.createElement("div");
  head.className = `gridHeadCell gridHead-${kind}`;
  if (rowColor) head.style.setProperty("--row-color", rowColor);

  const lbl = document.createElement("div");
  lbl.className = "gridHeadLabel";
  lbl.textContent = kind === "row" ? labelText : labelText;
  head.appendChild(lbl);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "gridHeadBtn";
  btn.title = kind === "row"
    ? `Upload massal baris ${labelText} (isi A${labelText === "A" ? "" : ""}1..${labelText}${state.h})`
    : `Upload massal kolom ${labelText} (isi semua baris di kolom ${labelText})`;
  btn.innerHTML = "&#8593;"; // ikon upload sederhana
  head.appendChild(btn);

  const input = document.createElement("input");
  input.type = "file";
  input.accept = "video/*";
  input.multiple = true;
  input.style.display = "none";
  head.appendChild(input);

  btn.addEventListener("click", () => {
    if (state.locked) return;
    input.value = "";
    input.click();
  });

  input.addEventListener("change", async () => {
    if (!input.files || !input.files.length) return;
    const files = Array.from(input.files);
    if (kind === "row") {
      await massUploadRow(index, files);
    } else {
      await massUploadCol(index, files);
    }
  });

  return head;
}

function _cellCoordsForRow(r) {
  const out = [];
  for (let c = 0; c < state.h; c++) out.push([r, c]);
  return out;
}
function _cellCoordsForCol(c) {
  const out = [];
  for (let r = 0; r < state.v; r++) out.push([r, c]);
  return out;
}

async function _massUploadCoords(coords, files, contextLabel) {
  if (state.locked) return;
  const slots = coords.length;
  const usable = files.slice(0, slots);
  const skipped = files.length - usable.length;

  // Upload berurutan (bukan paralel) supaya status tiap sel ter-update
  // rapi dan tidak membanjiri server dengan banyak request sekaligus.
  for (let i = 0; i < usable.length; i++) {
    const [r, c] = coords[i];
    await uploadCell(r, c, usable[i]);
  }

}

async function massUploadRow(r, files) {
  const rowLabel = String.fromCharCode(65 + r);
  await _massUploadCoords(_cellCoordsForRow(r), files, `baris ${rowLabel}`);
}

async function massUploadCol(c, files) {
  await _massUploadCoords(_cellCoordsForCol(c), files, `kolom ${c + 1}`);
}


async function uploadCell(r, c, file) {
  if (state.locked) return;

  const cellData = state.grid[r][c];
  const cellEl = $(`cell_${r}_${c}`);
  const iconEl = $(`icon_${r}_${c}`);
  const textEl = $(`text_${r}_${c}`);
  const statusEl = $(`status_${r}_${c}`);

  cellData.uploading = true;
  cellData.error = null;
  if (cellEl) {
    cellEl.classList.remove("success", "error");
    cellEl.classList.add("uploading");
    cellEl.setAttribute("aria-label", `${cellData.label}, sedang mengunggah ${file.name}`);
  }
  if (iconEl) iconEl.textContent = "…";
  if (textEl) { textEl.textContent = file.name; textEl.title = file.name; }
  if (statusEl) statusEl.textContent = "Mengunggah…";
  syncCellInspector();

  const fd = new FormData();
  fd.append("file", file);
  fd.append("label", cellData.label);

  try {
    const resp = await fetch("/api/upload", { method: "POST", body: fd });
    const json = await resp.json();
    if (!json.ok) throw new Error(json.error || "upload_failed");

    cellData.path = json.path;
    cellData.filename = file.name;
    if (cellEl) {
      cellEl.classList.remove("uploading", "error");
      cellEl.classList.add("success");
      cellEl.title = `${cellData.label} — ${file.name}`;
      cellEl.setAttribute("aria-label", `${cellData.label}, terisi ${file.name}`);
    }
    if (iconEl) iconEl.textContent = "✓";
    if (textEl) { textEl.textContent = file.name; textEl.title = file.name; }
    if (statusEl) statusEl.textContent = "Terunggah";
    await loadStorageUsage();
  } catch (e) {
    cellData.path = null;
    cellData.filename = null;
    cellData.error = String(e.message || e);
    if (cellEl) {
      cellEl.classList.remove("uploading", "success");
      cellEl.classList.add("error");
      cellEl.title = `${cellData.label} — gagal: ${cellData.error}`;
      cellEl.setAttribute("aria-label", `${cellData.label}, upload gagal`);
    }
    if (iconEl) iconEl.textContent = "!";
    if (textEl) { textEl.textContent = "Gagal upload"; textEl.title = cellData.error; }
    if (statusEl) statusEl.textContent = "Gagal";
  } finally {
    cellData.uploading = false;
    syncCellInspector();
    resetBelow(2);
    updateGridValidity();
  }
}

function isGridComplete() {
  if (!state.grid.length) return false;
  for (const row of state.grid) {
    for (const cell of row) {
      if (!cell.path) return false;
      if (cell.uploading) return false;
    }
  }
  return true;
}

function updateGridValidity() {
  const complete = isGridComplete();
  const renderReady = complete && !!state.estimates;
  updateGridSummary();
  syncCellInspector();

  gridHint.hidden = false;
  if (!state.h || !state.v) {
    gridHint.textContent = "Pilih ukuran matriks untuk mulai mengisi video.";
  } else if (!complete) {
    gridHint.textContent = "Lengkapi semua sel. Upload massal per baris/kolom tersedia pada header grid.";
  } else if (!state.estimates) {
    gridHint.textContent = "Grid lengkap. Kalkulasi mode render sedang disiapkan…";
  } else {
    gridHint.textContent = "";
    gridHint.hidden = true;
  }

  setEnabled(sec5, renderReady);
  if (btnGoRender) btnGoRender.disabled = !renderReady || state.locked;
  updateGenerateEnabled();
  syncWorkflowTabs();
}

const MODE_ESTIMATE_UI = [
  { key: "horizontal", input: mHorizontal, maxId: "maxHorizontal", setupMaxId: "setupMaxHorizontal" },
  { key: "mixHorizontal", input: mMixHorizontal, maxId: "maxMixHorizontal", setupMaxId: "setupMaxMixHorizontal" },
  { key: "mixHorizontalLinear", input: mMixHorizontalLinear, maxId: "maxMixHorizontalLinear", setupMaxId: "setupMaxMixHorizontalLinear" },
  { key: "mixHorizontalLinearUnique", input: mMixHorizontalLinearUnique, maxId: "maxMixHorizontalLinearUnique", setupMaxId: "setupMaxMixHorizontalLinearUnique" },
];

function formatCombinationCount(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value.toLocaleString("id-ID", { maximumFractionDigits: 0 });
  }
  const raw = String(value ?? "0");
  if (/^\d+$/.test(raw)) return raw.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return raw;
}

// JSON number di browser kehilangan presisi setelah Number.MAX_SAFE_INTEGER.
// Untuk tampilan estimasi maksimum grid sampai 10×10, hitung ulang dengan
// BigInt menggunakan rumus yang sama seperti calculator.py. Ini hanya untuk
// presentasi angka; validitas dan rencana render tetap berasal dari backend.
function permCountBigInt(n, k) {
  if (k < 0 || k > n) return 0n;
  let out = 1n;
  for (let i = n; i > n - k; i -= 1) out *= BigInt(i);
  return out;
}

function exactMaxCountsForDisplay(valid) {
  const h = Number(state.h || 0);
  const v = Number(state.v || 0);
  const factorialH = permCountBigInt(h, h);
  const powVH = BigInt(v) ** BigInt(h);
  return {
    horizontal: valid.horizontal ? String(BigInt(v) * factorialH) : "0",
    mixHorizontal: valid.mixHorizontal ? String(powVH * factorialH) : "0",
    mixHorizontalLinear: valid.mixHorizontalLinear ? String(powVH) : "0",
    mixHorizontalLinearUnique: valid.mixHorizontalLinearUnique ? String(permCountBigInt(v, h)) : "0",
  };
}

function renderEstimates(est) {
  const exactMax = exactMaxCountsForDisplay(est.valid);
  for (const item of MODE_ESTIMATE_UI) {
    const valid = !!est.valid[item.key];
    const max = exactMax[item.key] ?? est.max[item.key] ?? 0;
    const maxEl = $(item.maxId);
    const setupMaxEl = $(item.setupMaxId);
    const validityEl = document.querySelector(`[data-mode-validity="${item.key}"]`);
    const card = document.querySelector(`[data-mode-card="${item.key}"]`);
    const setupValidityEl = document.querySelector(`[data-setup-validity="${item.key}"]`);
    const setupCard = document.querySelector(`[data-setup-estimate-card="${item.key}"]`);
    const formattedMax = formatCombinationCount(max);

    if (maxEl) { maxEl.textContent = formattedMax; maxEl.title = formattedMax; }
    if (setupMaxEl) { setupMaxEl.textContent = formattedMax; setupMaxEl.title = formattedMax; }
    if (validityEl) {
      validityEl.textContent = valid ? "Valid" : "Tidak valid";
      validityEl.className = `mode-validity ${valid ? "ok" : "no"}`;
    }
    if (card) {
      card.classList.toggle("valid", valid);
      card.classList.toggle("invalid", !valid);
    }
    if (setupValidityEl) {
      setupValidityEl.textContent = valid ? "Valid" : "Tidak valid";
      setupValidityEl.className = `setup-mode-validity ${valid ? "ok" : "no"}`;
    }
    if (setupCard) {
      setupCard.classList.toggle("valid", valid);
      setupCard.classList.toggle("invalid", !valid);
    }
    item.input.dataset.invalid = valid ? "0" : "1";
  }
  applyModeExclusivity();
}

function isInvalid(el) {
  return el.dataset.invalid === "1";
}

// Semua mode satu keluarga horizontal. Mode yang tidak valid untuk ukuran
// grid aktif otomatis dinonaktifkan dan tidak dapat ikut payload render.
function applyModeExclusivity() {
  [mHorizontal, mMixHorizontal, mMixHorizontalLinear, mMixHorizontalLinearUnique].forEach((el) => {
    el.disabled = isInvalid(el);
    if (isInvalid(el)) el.checked = false;
  });
}

function onModeChange() {
  applyModeExclusivity();
  updateGenerateEnabled();
  resetSizeEstimate();
}

let calcRequestSequence = 0;
async function doCalc() {
  if (!state.h || !state.v) return;
  const requestId = ++calcRequestSequence;
  setCalcStatus("Menghitung…", "pending");

  const payload = { h: state.h, v: state.v };
  const resp = await fetch("/api/calc", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const json = await resp.json();
  if (!json.ok) throw new Error(json.error || "calc_failed");
  if (requestId !== calcRequestSequence) return;

  state.estimates = { valid: json.valid, max: json.max };
  renderEstimates(state.estimates);
  setCalcStatus("Siap", "ok");
  resetSizeEstimate();
  updateGridValidity();
  updateGenerateEnabled();
}

function selectedModes() {
  return {
    horizontal: mHorizontal.checked && !mHorizontal.disabled,
    mixHorizontal: mMixHorizontal.checked && !mMixHorizontal.disabled,
    mixHorizontalLinear: mMixHorizontalLinear.checked && !mMixHorizontalLinear.disabled,
    mixHorizontalLinearUnique: mMixHorizontalLinearUnique.checked && !mMixHorizontalLinearUnique.disabled,
  };
}

function anyModeSelected(modes) {
  return Object.values(modes).some(Boolean);
}

function updateGenerateEnabled() {
  const modes = selectedModes();
  const ok = isGridComplete() && !!state.estimates && anyModeSelected(modes) && !state.locked;
  btnGenerate.disabled = !ok;
  updateSizeEstimateVisibility();
}

// ── Estimasi ukuran output (v1.1) ──
const MODE_LABELS = {
  horizontal: "Acak per Track",
  mixHorizontal: "Acak Lintas Track",
  mixHorizontalLinear: "Urutan Clip",
  mixHorizontalLinearUnique: "Urutan Clip — Track Unik",
};

function updateSizeEstimateVisibility() {
  if (!sizeEstimate) return;
  // Tampilkan blok estimasi bila input lengkap, kalkulasi otomatis tersedia,
  // dan minimal satu mode dipilih. Setiap perubahan mode mereset hasil lama.
  const show = isGridComplete() && !!state.estimates && anyModeSelected(selectedModes());
  sizeEstimate.hidden = !show;
  if (btnEstimateSize) btnEstimateSize.disabled = state.locked;
}

function resetSizeEstimate() {
  if (!sizeEstimateBody) return;
  sizeEstimateBody.innerHTML =
    '<p class="hint" style="margin:6px 0 0 0">Pilih minimal 1 mode, lalu klik "Hitung estimasi ukuran" untuk melihat perkiraan total GB.</p>';
}

async function estimateSize() {
  const modes = selectedModes();
  if (!anyModeSelected(modes)) {
    resetSizeEstimate();
    return;
  }

  const batch = { enabled: !!batchLimit.checked, size: null };
  if (batch.enabled) {
    const n = Number(batchSize.value || 0);
    batch.size = Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
  }

  const payload = {
    h: state.h,
    v: state.v,
    modes,
    batch,
    audioMode: getAudioMode(),
    // v1.6: estimasi ukuran memakai profil output yang dipilih user.
    outputProfile: readOutputProfile(),
    grid: state.grid.map((row) => row.map((c) => ({ label: c.label, path: c.path }))),
  };

  if (btnEstimateSize) {
    btnEstimateSize.disabled = true;
    btnEstimateSize.textContent = "Menghitung...";
  }

  try {
    const resp = await fetch("/api/estimate_size", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await resp.json();
    if (!json.ok) throw new Error(json.error || "estimate_failed");
    renderSizeEstimate(json);
  } catch (e) {
    sizeEstimateBody.innerHTML = `<p class="est-note est-warn">Gagal menghitung estimasi: ${String(e.message || e)}</p>`;
  } finally {
    if (btnEstimateSize) {
      btnEstimateSize.disabled = false;
      btnEstimateSize.textContent = "Hitung ulang estimasi";
    }
  }
}

function renderSizeEstimate(data) {
  const per = data.perMode || {};
  const modeKeys = Object.keys(per);

  if (!modeKeys.length) {
    resetSizeEstimate();
    return;
  }

  const a = data.assumptions || {};
  const avgDur = a.avgClipDuration != null ? a.avgClipDuration : 0;
  const muted = a.muteAudio != null ? a.muteAudio : true;
  // v1.6: tampilkan asumsi resolusi/fps/bitrate SESUNGGUHNYA dari profil yang
  // dipilih (dulu di-hardcode "1080×1920 @30fps ~8 Mbps · audio 192 kbps").
  const resStr = (a.width && a.height) ? `${a.width}×${a.height}` : "profil dipilih";
  const fpsStr = a.fps ? ` @${a.fps}fps` : "";
  const vbps = a.videoBitrate || 0;
  const bitrateStr = vbps >= 1e6 ? `~${(vbps / 1e6).toFixed(1)} Mbps` : `~${Math.round(vbps / 1e3)} kbps`;
  const audioStr = muted
    ? " (tanpa audio)"
    : ` + audio ${Math.round((a.audioBitrate || 0) / 1e3)} kbps`;
  const rateModeStr = a.rateMode === "bitrate"
    ? "bitrate target (VBR terbatas)"
    : `CRF ${a.quality != null ? a.quality : ""} (kualitas tetap, bitrate menyesuaikan)`;

  let rows = "";
  for (const m of modeKeys) {
    const info = per[m];
    rows += `<tr>
      <td class="est-mode">${MODE_LABELS[m] || m}</td>
      <td class="num">${info.outputs.toLocaleString("id-ID")}</td>
      <td class="num">${info.durationPerOutput}s</td>
      <td class="num est-size">${formatBytes(info.totalBytes)}</td>
    </tr>`;
  }

  const missingNote =
    data.missingClips > 0
      ? `<div class="est-note est-warn">&#9888; ${data.missingClips} klip tidak bisa dibaca durasinya — estimasi memakai rata-rata dari klip yang terbaca.</div>`
      : "";

  const durNote =
    avgDur > 0
      ? `Rata-rata durasi klip: <b>${avgDur}s</b>.`
      : `<span class="est-warn">Durasi klip tidak terbaca (0s) — estimasi jadi 0. Pastikan file video valid.</span>`;

  sizeEstimateBody.innerHTML = `
    <div class="est-total">
      <span class="num">${formatBytes(data.grandTotalBytes)}</span>
      <span class="lbl">total perkiraan untuk ${data.grandTotalOutputs.toLocaleString("id-ID")} video</span>
    </div>
    <table class="est-table">
      <thead>
        <tr><th>Mode</th><th class="num">Jumlah Output</th><th class="num">Durasi/Video</th><th class="num">Estimasi Ukuran</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    ${missingNote}
    <div class="est-note">
      ${durNote} Asumsi bitrate video ${bitrateStr}${audioStr}, resolusi ${resStr}${fpsStr}, ${rateModeStr}.
      Angka ini <b>perkiraan aman (cenderung sedikit lebih besar)</b> — ukuran nyata tergantung isi video. Video sederhana/statis bisa jauh lebih kecil; video ramai gerakan mendekati angka ini.
    </div>`;
}

function lockUI(lock) {
  state.locked = lock;
  document.body.classList.toggle("locked", !!lock);
  // Keep progress usable even when locked.
  progressWrap.style.pointerEvents = "auto";
}

// v1.5: format detik → "1j 23m 45d" agar ETA panjang mudah dibaca.
function formatEta(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}j ${m}m ${s}d`;
  if (m > 0) return `${m}m ${s}d`;
  return `${s}d`;
}

// v1.5 FIX: chip tahap (Tahap 1/2 Normalisasi, Tahap 2/2 Render) — data
// `phase`/`prep` sudah dikirim backend sejak v1.4 tetapi tidak pernah
// ditampilkan oleh frontend.
function renderPhaseChip(status) {
  if (!phaseChip) return;
  let text = "";
  let cls = "chip";
  if (status.status === "running") {
    if (status.phase === "prepare") {
      const p = status.prep || {};
      const t = p.total || 0;
      text = t > 0 ? `Tahap 1/2 — Normalisasi ${p.done ?? 0}/${t}` : "Menyiapkan…";
      cls = "chip busy";
    } else {
      text = "Tahap 2/2 — Render";
      cls = "chip busy";
    }
  } else if (status.status === "done") {
    text = "Selesai";
    cls = "chip ok";
  } else if (status.status === "cancelled") {
    text = "Dihentikan";
    cls = "chip err";
  } else if (status.status === "error") {
    text = "Error";
    cls = "chip err";
  }
  phaseChip.className = cls;
  phaseChip.textContent = text;
}

function renderProgress(status) {
  const done = status.done ?? 0;
  const total = status.total ?? 0;
  const eta = status.etaSeconds != null ? ` | ETA ~ ${formatEta(status.etaSeconds)}` : "";
  globalLine.textContent = `Status: ${status.status} | ${done}/${total}${eta}`;

  renderPhaseChip(status);

  // v1.5 FIX: bar progres global besar (#globalBarFill) tidak pernah diisi.
  // Saat tahap normalisasi, bar mengikuti progres normalisasi; saat render,
  // mengikuti progres output.
  if (globalBarFill) {
    let pct = total ? (done / total) * 100 : 0;
    if (status.status === "running" && status.phase === "prepare") {
      const p = status.prep || {};
      pct = p.total ? ((p.done || 0) / p.total) * 100 : 0;
    } else if (status.status === "done") {
      pct = 100;
    }
    globalBarFill.style.width = pct.toFixed(2) + "%";
  }

  // v1.5 FIX: tampilkan folder output final (meta.outputDir dari backend).
  if (outDirLine) {
    const outDir = status.meta && status.meta.outputDir;
    if (outDir && status.status !== "running") {
      outDirLine.textContent = `Hasil tersimpan di: ${outDir}`;
      outDirLine.hidden = false;
    }
  }

  perModeProgress.innerHTML = "";
  const per = status.perMode || {};
  for (const [mode, st] of Object.entries(per)) {
    const wrap = document.createElement("div");
    wrap.className = "pitem";

    const meta = document.createElement("div");
    meta.className = "pmeta";
    meta.innerHTML = `<div>${mode}</div><div>${st.done}/${st.total}</div>`;

    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("div");
    const pct = st.total ? (st.done / st.total) * 100 : 0;
    fill.style.width = pct.toFixed(2) + "%";
    bar.appendChild(fill);

    wrap.appendChild(meta);
    wrap.appendChild(bar);
    perModeProgress.appendChild(wrap);
  }

  const logs = (status.logs || []).slice(-20);
  logEl.textContent = logs.length ? logs.join("\n\n") : "";
}

// v1.5 FIX: dulu satu kali gagal fetch (server restart / jaringan putus
// sesaat) menghentikan polling selamanya dan UI tetap terkunci. Kini gagal
// sementara di-retry; menyerah hanya setelah beberapa kegagalan beruntun.
let pollFailures = 0;
const POLL_MAX_FAILURES = 8;

async function poll(jobId) {
  let json;
  try {
    const resp = await fetch(`/api/status/${jobId}`);
    json = await resp.json();
    pollFailures = 0;
  } catch (e) {
    pollFailures += 1;
    if (pollFailures < POLL_MAX_FAILURES) {
      setTimeout(() => poll(jobId), 2000); // coba lagi
      return;
    }
    // Menyerah: buka kunci UI supaya tidak macet, beri tahu user.
    logEl.textContent =
      "Koneksi ke server terputus saat memantau progres. " +
      "Render kemungkinan masih berjalan di server — muat ulang halaman untuk mengecek.";
    state.currentJobId = null;
    state.stopping = false;
    showStopButton(false);
    lockUI(false);
    updateGridValidity();
    updateGenerateEnabled();
    return;
  }

  renderProgress(json);
  if (json.status === "running") {
    setTimeout(() => poll(jobId), 800);
  } else {
    // Job selesai / dibatalkan / error → sembunyikan Stop, buka kunci UI.
    state.currentJobId = null;
    state.stopping = false;
    showStopButton(false);
    lockUI(false);
    updateGridValidity();
    updateGenerateEnabled();
  }
}

function showStopButton(show) {
  if (!btnStop) return;
  btnStop.hidden = !show;
  if (show) {
    btnStop.disabled = false;
    btnStop.innerHTML = "&#9632; Stop";
  }
}

async function stopGenerate() {
  if (!state.currentJobId || state.stopping) return;
  const yes = confirm(
    "Hentikan proses generate?\n\n" +
    "Video yang SUDAH selesai tetap tersimpan. " +
    "Video yang sedang diproses saat ini akan dibatalkan dan file setengah jadinya dihapus."
  );
  if (!yes) return;

  state.stopping = true;
  if (btnStop) {
    btnStop.disabled = true;
    btnStop.innerHTML = "Menghentikan...";
  }
  try {
    await fetch(`/api/stop/${state.currentJobId}`, { method: "POST" });
    // Status akhir ('cancelled') akan tertangkap oleh poll() berikutnya.
  } catch (e) {
    // Bila gagal mengirim sinyal, kembalikan tombol agar bisa dicoba lagi.
    state.stopping = false;
    if (btnStop) {
      btnStop.disabled = false;
      btnStop.innerHTML = "&#9632; Stop";
    }
    logEl.textContent = `Gagal mengirim perintah Stop: ${String(e.message || e)}`;
  }
}

function localTimeMetadata() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return {
    clientTimeZone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
    clientUtcOffsetMinutes: now.getTimezoneOffset(),
    clientLocalStartedAt: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
    clientRunTag: `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`,
  };
}

function formatIntegerString(value) {
  const raw = String(value ?? "0").replace(/[^0-9-]/g, "");
  try {
    return BigInt(raw || "0").toLocaleString("id-ID");
  } catch (_) {
    return String(value ?? "0");
  }
}

function hideLargeOutputWarning() {
  if (largeOutputModal) largeOutputModal.style.display = "none";
  pendingLargeOutput = null;
}

function showLargeOutputWarning(payload, warning) {
  pendingLargeOutput = { payload, token: warning.confirmationToken };
  if (largeOutputCount) largeOutputCount.textContent = formatIntegerString(warning.totalOutputs);
  if (largeOutputThreshold) largeOutputThreshold.textContent = formatIntegerString(warning.threshold);
  if (largeOutputGrid) largeOutputGrid.textContent = warning.grid || `${payload.h} × ${payload.v}`;
  if (largeOutputModes) {
    const perMode = warning.perMode || {};
    largeOutputModes.innerHTML = Object.entries(perMode).map(([key, count]) =>
      `<div><span>${MODE_LABELS[key] || key}</span><strong class="mono">${formatIntegerString(count)} video</strong></div>`
    ).join("");
  }
  if (largeOutputModal) largeOutputModal.style.display = "flex";
}

async function submitGeneratePayload(payload) {
  progressWrap.hidden = false;
  if (outDirLine) { outDirLine.hidden = true; outDirLine.textContent = ""; }
  lockUI(true);

  let resp;
  let json;
  try {
    resp = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    json = await resp.json();
  } catch (e) {
    logEl.textContent = `Gagal memulai job (server tidak merespons): ${String(e.message || e)}`;
    lockUI(false);
    return;
  }

  if (resp.status === 409 && json.error === "large_output_confirmation_required" && json.warning) {
    progressWrap.hidden = true;
    lockUI(false);
    showLargeOutputWarning(payload, json.warning);
    return;
  }
  if (!json.ok) {
    logEl.textContent = json.error || "start_failed";
    lockUI(false);
    return;
  }
  state.currentJobId = json.jobId;
  state.stopping = false;
  showStopButton(true);
  poll(json.jobId);
}

async function startGenerate() {
  const modes = selectedModes();

  // v1.9: validasi mode audio Replace/Mix butuh minimal 1 file audio.
  const audioMode = getAudioMode();
  if ((audioMode === "replace" || audioMode === "mix") && state.audioFiles.length === 0) {
    logEl.textContent = `Mode audio "${audioMode}" dipilih tetapi belum ada file audio ter-upload. Upload minimal 1 file audio dulu, atau pilih mode Mute/Keep.`;
    return;
  }

  // Batch option
  const batch = {
    enabled: !!batchLimit.checked,
    size: null,
  };
  if (batch.enabled) {
    const n = Number(batchSize.value || 0);
    if (!Number.isFinite(n) || n <= 0) {
      logEl.textContent = "Batch Size harus diisi angka > 0 (atau pilih Tanpa limit).";
      return;
    }
    batch.size = Math.floor(n);
  }

  const payload = {
    h: state.h,
    v: state.v,
    modes,
    batch,
    audioMode,
    audioFiles: state.audioFiles.map((a) => a.path),
    encoderMode: encoderMode ? String(encoderMode.value || "auto") : "auto",
    // v1.5 FIX: opsi panel Performa kini benar-benar terkirim ke backend.
    renderMethod: renderMethod ? String(renderMethod.value || "classic") : "classic",
    parallelWorkers: parallelWorkers ? String(parallelWorkers.value || "auto") : "auto",
    // v1.6: profil output (resolusi/fps/kualitas/bitrate) dipilih user.
    outputProfile: readOutputProfile(),
    folderPolicy: resolveFolderPolicy(),
    grid: state.grid.map((row) => row.map((c) => ({ label: c.label, path: c.path }))),
    ...localTimeMetadata(),
  };

  await submitGeneratePayload(payload);
}

if (btnReviewLargeOutput) btnReviewLargeOutput.addEventListener("click", hideLargeOutputWarning);
if (btnConfirmLargeOutput) btnConfirmLargeOutput.addEventListener("click", async () => {
  if (!pendingLargeOutput) return;
  const confirmed = {
    ...pendingLargeOutput.payload,
    largeOutputConfirmation: pendingLargeOutput.token,
  };
  hideLargeOutputWarning();
  await submitGeneratePayload(confirmed);
});
if (largeOutputModal) largeOutputModal.addEventListener("click", (event) => {
  if (event.target === largeOutputModal) hideLargeOutputWarning();
});

// UI-only events v1.16
workflowTabs.forEach((tab) => tab.addEventListener("click", () => openWorkspaceTab(tab.dataset.tabTarget)));
if (btnInspectorUpload) {
  btnInspectorUpload.addEventListener("click", () => {
    if (!state.selectedCell || state.locked) return;
    const { r, c } = state.selectedCell;
    const input = $(`input_${r}_${c}`);
    if (input) {
      input.value = "";
      input.click();
    }
  });
}
window.addEventListener("resize", scheduleGridLayout);

// Events
function handleMatrixChange() {
  if (state.locked) return;
  // Batalkan hasil kalkulasi lama bila ukuran berubah atau kembali kosong.
  calcRequestSequence += 1;
  state.h = Number(hSelect.value || 0);
  state.v = Number(vSelect.value || 0);
  resetBelow(1);

  const ready = state.h > 0 && state.v > 0;
  setEnabled(sec2, ready);
  setEnabled(sec5, false);
  updateOutputStructure();
  updateMatrixSummary();
  openWorkspaceTab("setup", true);

  if (!ready) {
    updateGridValidity();
    return;
  }

  buildGrid();
  doCalc().catch((e) => {
    if (!state.h || !state.v) return;
    state.estimates = null;
    resetModeEstimateUI();
    setCalcStatus("Gagal menghitung", "error");
    setEnabled(sec5, false);
    logEl.textContent = `Kalkulasi kombinasi gagal: ${String(e.message || e)}`;
    updateGridValidity();
  });
}

hSelect.addEventListener("change", handleMatrixChange);
vSelect.addEventListener("change", handleMatrixChange);

if (btnGoRender) {
  btnGoRender.addEventListener("click", () => openWorkspaceTab("render"));
}

[mHorizontal, mMixHorizontal, mMixHorizontalLinear, mMixHorizontalLinearUnique].forEach((el) =>
  el.addEventListener("change", onModeChange)
);
btnGenerate.addEventListener("click", startGenerate);
if (btnStop) btnStop.addEventListener("click", stopGenerate);
if (btnEstimateSize) btnEstimateSize.addEventListener("click", estimateSize);

// Batch UI
[batchNone, batchLimit].forEach((el) => el.addEventListener("change", () => {
  syncBatchUI();
  resetSizeEstimate();
}));
if (batchSize) batchSize.addEventListener("input", resetSizeEstimate);
// v1.6: mute juga menampilkan/menyembunyikan kolom bitrate audio.
audioModeRadios.forEach((r) => r.addEventListener("change", () => {
  syncOutputProfileUI();
  syncAudioModeUI();
}));

// v1.6: kontrol Kualitas output.
if (qualityPreset) qualityPreset.addEventListener("change", applyQualityPreset);
// Perubahan manual pada kontrol detail → preset menjadi "Kustom".
[resPreset, fpsSelect, rateMode, qualitySelect].forEach((el) => {
  if (el) el.addEventListener("change", markPresetCustom);
});
[resCustomW, resCustomH, videoBitrateK, audioBitrateK].forEach((el) => {
  if (el) el.addEventListener("input", markPresetCustom);
});

// Storage UI - Open custom folder selector modal
if (btnBrowseStorage) {
  btnBrowseStorage.addEventListener("click", () => {
    openStorageModal();
  });
}

// Modal Event Listeners
if (closeStorageModal) {
  closeStorageModal.addEventListener("click", closeStorageModalFn);
}
if (btnCancelStorageModal) {
  btnCancelStorageModal.addEventListener("click", closeStorageModalFn);
}

// Go Up folder
if (btnStorageUp) {
  btnStorageUp.addEventListener("click", () => {
    const parentPath = btnStorageUp.dataset.parent;
    if (parentPath) {
      loadModalDirectory(parentPath);
    }
  });
}

// Confirm folder selection
if (btnSelectStorageFolder) {
  btnSelectStorageFolder.addEventListener("click", () => {
    if (modalSelectedPath) {
      state.storageBase = modalSelectedPath;
      if (storagePath) storagePath.value = modalSelectedPath;
      logEl.textContent = `Folder terpilih: ${modalSelectedPath}. Klik 'Terapkan' untuk mengaktifkan.`;
      closeStorageModalFn();
    }
  });
}

// Apply Storage Base
if (btnApplyStorage) {
  btnApplyStorage.addEventListener("click", async () => {
    try {
      btnApplyStorage.disabled = true;
      await setStorageBase(storagePath.value);
      logEl.textContent = `Storage folder berhasil diterapkan ke: ${state.storageBase}`;
    } catch (e) {
      logEl.textContent = `Gagal menerapkan storage: ${String(e.message || e)}`;
    } finally {
      btnApplyStorage.disabled = false;
    }
  });
}

// Reset Storage Base
if (btnResetStorage) {
  btnResetStorage.addEventListener("click", async () => {
    try {
      btnResetStorage.disabled = true;
      await setStorageBase("");
      logEl.textContent = `Storage folder direset ke default: ${state.storageBase}`;
    } catch (e) {
      logEl.textContent = `Gagal me-reset storage: ${String(e.message || e)}`;
    } finally {
      btnResetStorage.disabled = false;
    }
  });
}

// Storage Usage Actions
if (btnRefreshUsage) {
  btnRefreshUsage.addEventListener("click", async () => {
    try {
      btnRefreshUsage.disabled = true;
      btnRefreshUsage.innerHTML = "...";
      await loadStorageUsage();
    } finally {
      btnRefreshUsage.disabled = false;
      // v1.5 FIX: label dikembalikan sesuai HTML ("Muat ulang", bukan "Refresh").
      btnRefreshUsage.innerHTML = "&#8635; Muat ulang";
    }
  });
}
if (btnCleanUploads) {
  btnCleanUploads.addEventListener("click", async () => {
    if (confirm("Apakah Anda yakin ingin menghapus semua file di folder 'uploads'? Tindakan ini tidak dapat dibatalkan.")) {
      await cleanStorage(["uploads"]);
    }
  });
}
if (btnCleanOutputs) {
  btnCleanOutputs.addEventListener("click", async () => {
    if (confirm("Apakah Anda yakin ingin menghapus semua hasil render di folder 'outputs'? Tindakan ini tidak dapat dibatalkan.")) {
      await cleanStorage(["outputs"]);
    }
  });
}
if (btnCleanAudio) {
  btnCleanAudio.addEventListener("click", async () => {
    if (confirm("Apakah Anda yakin ingin menghapus semua file di folder 'audio'? Tindakan ini tidak dapat dibatalkan.")) {
      await cleanStorage(["audio"]);
      await loadAudioList();
    }
  });
}
if (btnCleanAll) {
  btnCleanAll.addEventListener("click", async () => {
    if (confirm("Apakah Anda yakin ingin menghapus semua file (uploads, temp, outputs, dan audio) di storage?")) {
      await cleanStorage(["uploads", "outputs", "temp", "audio"]);
      await loadAudioList();
    }
  });
}

// Close modal when clicking outside of modal-content
window.addEventListener("click", (event) => {
  if (storageModal && event.target === storageModal) {
    closeStorageModalFn();
  }
});

// Initial state
applyGridLayout();
openWorkspaceTab("setup", true);
setEnabled(sec2, false);
setEnabled(sec5, false);
updateMatrixSummary();
updateGridSummary();
syncWorkflowTabs();

updateOutputStructure();

// Init misc
syncBatchUI();
syncOutputProfileUI(); // v1.6: set visibilitas kontrol kualitas + footer awal
syncAudioModeUI();     // v1.9: sembunyikan/tampilkan panel upload audio sesuai mode
loadAudioList();       // v1.9: muat daftar audio yang sudah pernah diupload
loadStorageBase();
loadSystemInfo(); // v1.5 FIX: isi chip sistem & hint encoder (dulu tidak pernah dipanggil)
