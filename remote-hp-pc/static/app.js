/* ============================================
   Remote HP — Frontend (app.js)
   ============================================ */

const API = {
  async get(url) {
    const r = await fetch(url);
    if (!r.ok) throw await r.json().catch(() => ({ error: r.statusText }));
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw await r.json().catch(() => ({ error: r.statusText }));
    return r.json();
  },
  async put(url, body) {
    const r = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw await r.json().catch(() => ({ error: r.statusText }));
    return r.json();
  },
  async del(url, body) {
    const opts = { method: "DELETE" };
    if (body !== undefined) {
      opts.headers = { "Content-Type": "application/json" };
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(url, opts);
    if (!r.ok) throw await r.json().catch(() => ({ error: r.statusText }));
    return r.json();
  },
};

// ── Konstanta slot aplikasi (v1.1.7) — sinkron dengan routes/accounts.py ──
const APP_SLOTS = ["original", "kloning"];
const SLOT_LABELS = { original: "Apk Original", kloning: "Apk Kloning" };
const SLOT_ICON = { original: "📱", kloning: "📲" };
const MAX_ACCOUNTS_PER_SLOT = 8;

// ── Global state ──
const state = {
  devices: [],
  accounts: {},        // device_id -> [accounts]
  selectedDevice: null,
  selectedAccount: null,
  currentPage: "dashboard",
};

// ════════════════════════════════════════
// TOAST
// ════════════════════════════════════════
function toast(message, type = "info", duration = 3000) {
  const wrap = document.getElementById("toastWrap");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  wrap.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.3s";
    setTimeout(() => el.remove(), 300);
  }, duration);
}

// ════════════════════════════════════════
// MODAL HELPER
// ════════════════════════════════════════
const Modal = {
  open({ title, bodyHtml, footerButtons }) {
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalBody").innerHTML = bodyHtml;
    const footer = document.getElementById("modalFooter");
    footer.innerHTML = "";
    (footerButtons || []).forEach((btn) => {
      const b = document.createElement("button");
      b.className = btn.class || "btn btn-ghost";
      b.textContent = btn.label;
      b.onclick = btn.onClick;
      if (btn.id) b.id = btn.id;
      footer.appendChild(b);
    });
    document.getElementById("modalOverlay").classList.add("show");
  },
  close() {
    document.getElementById("modalOverlay").classList.remove("show");
  },
};

document.getElementById("modalClose").onclick = () => Modal.close();
document.getElementById("modalOverlay").onclick = (e) => {
  if (e.target.id === "modalOverlay") Modal.close();
};

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function copyText(text, options = {}) {
  const silent = !!options.silent;
  return navigator.clipboard.writeText(text).then(
    () => {
      if (!silent) toast("Disalin ke clipboard ✓", "success", 1500);
      return true;
    },
    () => {
      if (!silent) toast("Gagal menyalin", "error");
      return false;
    }
  );
}

// ════════════════════════════════════════
// NAVIGATION
// ════════════════════════════════════════
function switchPage(page) {
  state.currentPage = page;
  document.querySelectorAll(".nav-item[data-page]").forEach((n) => {
    n.classList.toggle("active", n.dataset.page === page);
  });
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  const target = document.getElementById(`page-${page}`);
  if (target) target.classList.add("active");

  if (page === "dashboard") {
    updateStats();
    loadHistory();
  }
  if (page === "settings") loadSettings();
  closeSidebarOnCompact();
}

document.addEventListener("click", (e) => {
  const navEl = e.target.closest("[data-page]");
  if (navEl) {
    switchPage(navEl.dataset.page);
  }
});

// ════════════════════════════════════════
// SIDEBAR: HP + AKUN
// ════════════════════════════════════════
async function loadDevices(checkStatus = false) {
  try {
    const url = checkStatus ? "/api/devices?check_status=1" : "/api/devices";
    state.devices = await API.get(url);
    // muat akun per device
    for (const d of state.devices) {
      state.accounts[d.id] = await API.get(`/api/accounts?device_id=${d.id}`);
    }
    renderSidebar();
    updateStats();
    // Riwayat kini menjadi bagian Dashboard; muat setelah data HP dan akun siap.
    if (state.currentPage === "dashboard") {
      await loadHistory();
    }
    // refresh topbar jika akun terpilih (status online bisa berubah)
    if (state.selectedAccount) {
      const dev = state.devices.find((d) => d.id === state.selectedDevice?.id);
      if (dev) state.selectedDevice = dev;
      renderTopbar();
    }
  } catch (err) {
    toast(err.error || "Gagal memuat HP", "error");
  }
}

function renderSidebar() {
  const list = document.getElementById("hpList");
  if (!state.devices.length) {
    list.innerHTML = `<div class="empty-state" style="padding:20px 10px">
      <div class="emoji">📱</div>
      <div class="title" style="font-size:13px">Belum ada HP</div>
      <div class="desc" style="font-size:12px">Klik "+ Tambah HP" di bawah.</div>
    </div>`;
    return;
  }

  list.innerHTML = state.devices
    .map((d) => {
      const accounts = state.accounts[d.id] || [];
      const isOnline = d.online === true; // status diisi oleh refresh ADB nanti
      const statusClass = isOnline ? "" : "offline";

      // v1.1.7: kelompokkan akun per SLOT APLIKASI (original / kloning).
      // 1 HP Xiaomi/Redmi: TikTok original + TikTok kloning (Aplikasi Ganda),
      // masing-masing maks 8 akun → 16 per HP.
      const groupHtml = APP_SLOTS.map((slot) => {
        const inSlot = accounts.filter(
          (a) => (a.app_slot || "original") === slot
        );
        const rows = inSlot
          .map((a) => {
            const active =
              state.selectedAccount && state.selectedAccount.id === a.id ? "active" : "";
            const username = escapeHtml(a.username);
            // v1.46: tandai akun yang juga ditempatkan di HP lain (akun
            // lintas-HP) dengan badge kecil, supaya kelihatan dari sidebar
            // tanpa perlu buka detail akun.
            const multiHpBadge = a._multi_hp
              ? `<span class="acc-multi-hp" title="Akun ini juga ada di HP lain">⇄</span>`
              : "";
            return `<div class="account-item ${active}" data-account="${a.id}" data-device="${d.id}" title="${username}">
              <span class="acc-name">${username}</span>${multiHpBadge}
            </div>`;
          })
          .join("");
        const full = inSlot.length >= MAX_ACCOUNTS_PER_SLOT;
        const addRow = full
          ? `<div class="account-item slot-full" title="Slot ini penuh (maks ${MAX_ACCOUNTS_PER_SLOT})">
               <span class="acc-full-label">Penuh (${MAX_ACCOUNTS_PER_SLOT}/${MAX_ACCOUNTS_PER_SLOT})</span>
             </div>`
          : `<div class="account-item account-add" data-add-account="${d.id}" data-slot="${slot}">
               <span class="acc-add-label">+ Tambah Akun</span>
             </div>`;
        return `<div class="slot-group">
          <div class="slot-head">
            <span class="slot-name">${SLOT_ICON[slot]} ${escapeHtml(SLOT_LABELS[slot])}</span>
            <span class="slot-count">${inSlot.length}/${MAX_ACCOUNTS_PER_SLOT}</span>
          </div>
          ${rows}
          ${addRow}
        </div>`;
      }).join("");

      return `<div class="hp-card" data-hp="${d.id}">
        <div class="hp-card-header" data-device-toggle="${d.id}">
          <div class="hp-info">
            <div class="hp-status ${statusClass}"></div>
            <div>
              <div class="hp-name">${escapeHtml(d.name)} ${escapeHtml(d.label || "")}</div>
              <div class="hp-serial">${
                d.active_transport === "wifi"
                  ? `📶 Wi-Fi · ${escapeHtml(d.active_serial || d.wifi_endpoint || "—")}`
                  : d.active_transport === "usb"
                    ? `🔌 USB · ${escapeHtml(d.active_serial || d.usb_serial || "—")}`
                    : d.wifi_endpoint
                      ? `○ Offline · Wi-Fi ${escapeHtml(d.wifi_endpoint)}`
                      : d.usb_serial
                        ? `○ Offline · USB ${escapeHtml(d.usb_serial)}`
                        : "○ Belum dikonfigurasi"
              }</div>
            </div>
          </div>
          <div class="hp-card-actions">
            <button class="hp-mirror-btn icon-btn" data-mirror="${d.id}" title="Mirror layar HP (scrcpy)">🖥️</button>
          </div>
        </div>
        <div class="account-list">
          ${groupHtml}
        </div>
      </div>`;
    })
    .join("");

  // bind account click
  list.querySelectorAll("[data-account]").forEach((el) => {
    el.onclick = () => selectAccount(+el.dataset.device, +el.dataset.account);
  });
  // bind add account (bawa slot aplikasi yang dipilih)
  list.querySelectorAll("[data-add-account]").forEach((el) => {
    el.onclick = (e) => {
      e.stopPropagation();
      openAccountModal(+el.dataset.addAccount, null, el.dataset.slot || "original");
    };
  });
  // bind HP header (edit on long context) -> klik untuk edit via dblclick
  list.querySelectorAll("[data-device-toggle]").forEach((el) => {
    el.ondblclick = () => openDeviceModal(+el.dataset.deviceToggle);
  });
  // bind tombol Mirror (scrcpy)
  list.querySelectorAll("[data-mirror]").forEach((el) => {
    el.onclick = (e) => {
      e.stopPropagation();
      mirrorDevice(+el.dataset.mirror, el);
    };
  });
}

async function mirrorDevice(deviceId, btnEl) {
  const original = btnEl ? btnEl.textContent : null;
  if (btnEl) {
    btnEl.textContent = "⏳";
    btnEl.style.pointerEvents = "none";
  }
  try {
    const res = await API.post(`/api/devices/${deviceId}/mirror`, {});
    if (res.already_open) {
      toast("Jendela mirror HP ini sudah terbuka 🖥️", "info", 3000);
    } else {
      toast("Jendela mirror dibuka 🖥️ (cek layar Anda)", "success");
    }
  } catch (err) {
    toast(err.error || "Gagal membuka mirror", "error", 5000);
  } finally {
    if (btnEl) {
      btnEl.textContent = original || "🖥️";
      btnEl.style.pointerEvents = "";
    }
  }
}

async function selectAccount(deviceId, accountId) {
  state.selectedDevice = state.devices.find((d) => d.id === deviceId);
  const accounts = state.accounts[deviceId] || [];
  state.selectedAccount = accounts.find((a) => a.id === accountId);
  // reset upload state saat ganti akun
  if (typeof Upload !== "undefined") Upload.reset();
  renderSidebar();
  renderTopbar();
  renderAccountInfo();
  switchPage("upload");

  // cek apakah ada sesi aktif untuk akun ini → resume
  if (typeof Upload !== "undefined") {
    try {
      const res = await API.get(`/api/upload/active/${accountId}`);
      if (res.has_active && res.videos && res.videos.length) {
        Upload.session = {
          session_id: res.session.id,
          videos: res.videos,
          caption: { content: "(caption sebelumnya — generate ulang jika perlu)", hashtags: "", full: "", empty: false },
          schedule: [],
          target_dir: "",
        };
        Upload.consoleLines = [];
        toast("Melanjutkan sesi yang masih aktif", "info");
      }
    } catch (e) {
      /* tidak ada sesi aktif, abaikan */
    }
  }

  if (typeof renderUploadPanel === "function") renderUploadPanel();
}

function renderTopbar() {
  const bc = document.getElementById("breadcrumb");
  const status = document.getElementById("topbarStatus");
  const actions = document.getElementById("topbarActions");
  if (!state.selectedAccount) {
    bc.innerHTML = `<span class="muted">Pilih HP & akun untuk mulai</span>`;
    status.innerHTML = "";
    actions.innerHTML = "";
    return;
  }
  const slot = state.selectedAccount.app_slot || "original";
  bc.innerHTML = `${escapeHtml(state.selectedDevice.name)} <span class="muted" style="font-size:12px">/ ${SLOT_ICON[slot]} ${escapeHtml(SLOT_LABELS[slot] || slot)}</span> → <span>${escapeHtml(
    state.selectedAccount.username
  )}</span>`;
  const online = state.selectedDevice.online === true;
  status.innerHTML = online
    ? `<div class="tag tag-green">● Online</div>`
    : `<div class="tag tag-gray">● Offline</div>`;
  actions.innerHTML = `
    <button class="btn btn-ghost btn-sm" id="btnViewNotes">📋 Lihat Catatan</button>
    <button class="btn btn-ghost btn-sm" id="btnEditAcc">✏️ Edit Akun</button>`;
  document.getElementById("btnViewNotes").onclick = () => {
    Modal.open({
      title: `Catatan — ${state.selectedAccount.username}`,
      bodyHtml: `<div style="font-size:13px;line-height:1.6;color:var(--text)">${
        escapeHtml(state.selectedAccount.notes) || '<span class="muted">Tidak ada catatan.</span>'
      }</div>`,
      footerButtons: [{ label: "Tutup", class: "btn btn-ghost", onClick: Modal.close }],
    });
  };
  document.getElementById("btnEditAcc").onclick = () =>
    openAccountModal(state.selectedDevice.id, state.selectedAccount);
}

function renderAccountInfo() {
  const card = document.getElementById("infoAkunCard");
  const body = document.getElementById("infoAkunBody");
  // Panel Info Akun dihapus pada v1.23. Pertahankan guard ini agar
  // pemanggilan lama tidak menimbulkan error saat data akun diperbarui.
  if (!card || !body) return;
  if (!state.selectedAccount) {
    card.style.display = "none";
    return;
  }
  const a = state.selectedAccount;
  const slot = a.app_slot || "original";
  card.style.display = "";
  body.innerHTML = `
    <div class="info-row"><span class="k">Slot Aplikasi</span><span class="v">${SLOT_ICON[slot]} ${escapeHtml(SLOT_LABELS[slot] || slot)}</span></div>
    <div class="info-row"><span class="k">Username TikTok</span><span class="v mono">${escapeHtml(a.username)}</span></div>
    <div class="info-row"><span class="k">Email</span><span class="v">${escapeHtml(a.email) || "—"}</span></div>
    <div class="info-row"><span class="k">Password</span>
      <span class="v" style="display:flex;align-items:center;gap:8px;justify-content:flex-end">
        <span id="pwMask" style="letter-spacing:2px">••••••••</span>
        <span class="muted" id="pwToggle" style="cursor:pointer;font-size:11px;white-space:nowrap">👁️ Lihat</span>
      </span></div>
    <div class="info-row"><span class="k">No. HP Akun</span><span class="v">${escapeHtml(a.phone) || "—"}</span></div>
    <div class="info-row" style="align-items:flex-start"><span class="k">Catatan</span>
      <span class="v" style="color:var(--muted);font-size:12px;line-height:1.5">${
        escapeHtml(a.notes) || "—"
      }</span></div>`;
  const toggle = document.getElementById("pwToggle");
  if (toggle) {
    let shown = false;
    toggle.onclick = () => {
      shown = !shown;
      document.getElementById("pwMask").textContent = shown
        ? a.password || "(kosong)"
        : "••••••••";
      toggle.textContent = shown ? "🙈 Sembunyikan" : "👁️ Lihat";
    };
  }
  document.getElementById("btnEditAkunInfo").onclick = () =>
    openAccountModal(state.selectedDevice.id, state.selectedAccount);
}

// ════════════════════════════════════════
// MODAL: TAMBAH/EDIT HP
// ════════════════════════════════════════
function openDeviceModal(deviceId = null) {
  const device = deviceId ? state.devices.find((d) => d.id === deviceId) : null;
  const isEdit = !!device;
  Modal.open({
    title: isEdit ? "Edit HP" : "Tambah HP",
    bodyHtml: `
      <div class="form-group">
        <label class="form-label">Nama HP *</label>
        <input class="input" id="dvName" value="${escapeHtml(device?.name || "")}" placeholder="HP Utama">
      </div>
      <div class="form-group">
        <label class="form-label">Serial ADB USB</label>
        <div class="input-row">
          <input class="input" id="dvUsbSerial" value="${escapeHtml(device?.usb_serial || (device?.serial && !String(device.serial).includes(":") ? device.serial : ""))}" placeholder="5c9e64260221">
          <button type="button" id="dvDetect" class="btn btn-ghost">🔍 Deteksi ADB</button>
        </div>
        <div id="dvDetectResult" class="device-detect-result"></div>
        <span class="field-help">Serial USB disimpan sebagai transport, bukan identitas HP. Mengaktifkan Wi-Fi tidak akan mengubah HP ini menjadi device baru.</span>
      </div>
      <div class="form-group">
        <label class="form-label">Endpoint ADB Wi-Fi</label>
        <input class="input" id="dvWifiEndpoint" value="${escapeHtml(device?.wifi_endpoint || (device?.serial && String(device.serial).includes(":") ? device.serial : ""))}" placeholder="192.168.1.20:37123">
        <span class="field-help">Boleh kosong. Endpoint dapat diisi otomatis dari menu Pengaturan → Koneksi HP.</span>
      </div>
      <div class="form-group">
        <label class="form-label">Preferensi Koneksi</label>
        <select class="input" id="dvPreferredTransport">
          <option value="auto" ${(device?.preferred_transport || "auto") === "auto" ? "selected" : ""}>Otomatis — Wi-Fi utama, USB fallback</option>
          <option value="wifi" ${device?.preferred_transport === "wifi" ? "selected" : ""}>Prioritaskan Wi-Fi</option>
          <option value="usb" ${device?.preferred_transport === "usb" ? "selected" : ""}>Prioritaskan USB</option>
        </select>
        <label class="checkbox-row" style="margin-top:8px">
          <input type="checkbox" id="dvAutoReconnect" ${device?.wifi_auto_reconnect === false || device?.wifi_auto_reconnect === 0 ? "" : "checked"}>
          <span>Auto reconnect Wi-Fi saat aplikasi berjalan</span>
        </label>
      </div>
      ${isEdit ? `<div class="form-group"><label class="form-label">ID HP Stabil</label><input class="input mono" value="${escapeHtml(device?.stable_uid || "")}" readonly><span class="field-help">ID internal ini tidak berubah ketika berpindah USB ↔ Wi-Fi.</span></div>` : ""}
      <div class="form-group">
        <label class="form-label">Label / Emoji</label>
        <input class="input" id="dvLabel" value="${escapeHtml(device?.label || "")}" placeholder="📱">
      </div>
      <div class="form-group">
        <label class="form-label">Catatan</label>
        <textarea class="input" id="dvNotes" placeholder="Catatan bebas...">${escapeHtml(
          device?.notes || ""
        )}</textarea>
      </div>`,
    footerButtons: [
      ...(isEdit
        ? [
            {
              label: "🗑️ Hapus",
              class: "btn btn-danger",
              onClick: () => confirmDeleteDevice(device),
            },
          ]
        : []),
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: isEdit ? "Simpan" : "Tambah",
        class: "btn btn-primary",
        onClick: () => saveDevice(deviceId),
      },
    ],
  });

  // Bind tombol deteksi serial (hanya saat tambah baru)
  const detectBtn = document.getElementById("dvDetect");
  if (detectBtn) {
    detectBtn.onclick = async () => {
      const resultEl = document.getElementById("dvDetectResult");
      detectBtn.textContent = "⏳ Mendeteksi...";
      try {
        const res = await API.get("/api/devices/detect");
        if (!res.ok) {
          resultEl.innerHTML = `<span style="color:var(--danger)">${escapeHtml(
            res.error || "ADB tidak tersedia"
          )}</span>`;
          return;
        }
        const unregistered = res.available.filter((d) => !d.registered);
        if (!res.available.length) {
          resultEl.innerHTML = `<span class="muted">Tidak ada HP terhubung. Cek kabel USB & USB Debugging.</span>`;
        } else if (!unregistered.length) {
          resultEl.innerHTML = `<span class="muted">Semua HP terhubung sudah terdaftar.</span>`;
        } else {
          resultEl.innerHTML =
            `<div class="muted" style="margin-bottom:4px">Klik untuk pakai serial:</div>` +
            unregistered
              .map(
                (d) =>
                  `<button type="button" class="btn btn-ghost device-serial-choice ${
                    d.status === "device" ? "device-serial-ready" : "device-serial-warning"
                  }" data-serial="${escapeHtml(d.serial)}" data-transport="${escapeHtml(d.transport || (String(d.serial).includes(":") ? "wifi" : "usb"))}">${d.transport === "wifi" ? "📶" : "🔌"} ${escapeHtml(d.serial)} (${escapeHtml(d.status)})</button>`
              )
              .join("");
          resultEl.querySelectorAll("[data-serial]").forEach((tag) => {
            tag.onclick = () => {
              const targetId = tag.dataset.transport === "wifi" ? "dvWifiEndpoint" : "dvUsbSerial";
              document.getElementById(targetId).value = tag.dataset.serial;
              toast(tag.dataset.transport === "wifi" ? "Endpoint Wi-Fi dipilih ✓" : "Serial USB dipilih ✓", "success", 1500);
            };
          });
        }
      } catch (err) {
        resultEl.innerHTML = `<span style="color:var(--danger)">${escapeHtml(
          err.error || "Gagal deteksi"
        )}</span>`;
      } finally {
        detectBtn.textContent = "🔍 Deteksi HP";
      }
    };
  }
}

async function saveDevice(deviceId) {
  const payload = {
    name: document.getElementById("dvName").value.trim(),
    usb_serial: document.getElementById("dvUsbSerial").value.trim(),
    wifi_endpoint: document.getElementById("dvWifiEndpoint").value.trim(),
    preferred_transport: document.getElementById("dvPreferredTransport").value,
    wifi_auto_reconnect: document.getElementById("dvAutoReconnect").checked,
    label: document.getElementById("dvLabel").value.trim(),
    notes: document.getElementById("dvNotes").value.trim(),
  };
  if (!payload.name) return toast("Nama HP wajib diisi", "warning");
  try {
    if (deviceId) {
      await API.put(`/api/devices/${deviceId}`, payload);
      toast("HP diperbarui ✓", "success");
    } else {
      await API.post("/api/devices", payload);
      toast("HP ditambahkan ✓", "success");
    }
    Modal.close();
    await loadDevices();
  } catch (err) {
    toast(err.error || "Gagal menyimpan HP", "error");
  }
}

function confirmDeleteDevice(device) {
  Modal.open({
    title: "Hapus HP?",
    bodyHtml: `<div style="font-size:13px;line-height:1.6">
      Yakin ingin menghapus <strong>${escapeHtml(device.name)}</strong>?<br>
      <span class="muted">Semua akun & riwayat terkait HP ini akan ikut terhapus. Tindakan ini tidak bisa dibatalkan.</span>
    </div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: "Ya, Hapus",
        class: "btn btn-danger",
        onClick: async () => {
          try {
            await API.del(`/api/devices/${device.id}`);
            toast("HP dihapus", "success");
            if (state.selectedDevice?.id === device.id) {
              state.selectedDevice = null;
              state.selectedAccount = null;
              renderTopbar();
              renderAccountInfo();
            }
            Modal.close();
            await loadDevices();
          } catch (err) {
            toast(err.error || "Gagal menghapus", "error");
          }
        },
      },
    ],
  });
}

// ════════════════════════════════════════
// MODAL: TAMBAH/EDIT AKUN
// ════════════════════════════════════════
function openAccountModal(deviceId, account = null, defaultSlot = "original") {
  const isEdit = !!account;
  const currentSlot = (account && account.app_slot) || defaultSlot || "original";
  const slotOptions = APP_SLOTS.map(
    (s) =>
      `<option value="${s}" ${s === currentSlot ? "selected" : ""}>${SLOT_ICON[s]} ${SLOT_LABELS[s]}</option>`
  ).join("");
  Modal.open({
    title: isEdit ? "Edit Akun" : "Tambah Akun",
    bodyHtml: `
      <div class="form-group">
        <label class="form-label">Slot Aplikasi *</label>
        <select class="input" id="acAppSlot">${slotOptions}</select>
        <span class="muted" style="font-size:11.5px">Akun ini ada di aplikasi TikTok yang mana? <b>Original</b> = aplikasi bawaan, <b>Kloning</b> = aplikasi ganda (Dual Apps). Maks ${MAX_ACCOUNTS_PER_SLOT} akun per aplikasi.</span>
      </div>
      <div class="form-group">
        <label class="form-label">Username TikTok *</label>
        <input class="input" id="acUsername" value="${escapeHtml(account?.username || "")}" placeholder="@toko_darda_01">
      </div>
      <div class="form-group">
        <label class="form-label">Email</label>
        <input class="input" id="acEmail" value="${escapeHtml(account?.email || "")}" placeholder="email@gmail.com">
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input class="input" id="acPassword" value="${escapeHtml(account?.password || "")}" placeholder="password akun">
      </div>
      <div class="form-group">
        <label class="form-label">No. HP Akun</label>
        <input class="input" id="acPhone" value="${escapeHtml(account?.phone || "")}" placeholder="+62 812 xxxx xxxx">
      </div>
      <div class="form-group">
        <label class="form-label">Catatan</label>
        <textarea class="input" id="acNotes" placeholder="Catatan bebas...">${escapeHtml(
          account?.notes || ""
        )}</textarea>
      </div>`,
    footerButtons: [
      ...(isEdit
        ? [
            {
              label: "🗑️ Hapus",
              class: "btn btn-danger",
              onClick: () => confirmDeleteAccount(account),
            },
          ]
        : []),
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: isEdit ? "Simpan" : "Tambah",
        class: "btn btn-primary",
        onClick: () => saveAccount(deviceId, account?.id),
      },
    ],
  });
}

async function saveAccount(deviceId, accountId) {
  const payload = {
    device_id: deviceId,
    app_slot: document.getElementById("acAppSlot")?.value || "original",
    username: document.getElementById("acUsername").value.trim(),
    email: document.getElementById("acEmail").value.trim(),
    password: document.getElementById("acPassword").value.trim(),
    phone: document.getElementById("acPhone").value.trim(),
    notes: document.getElementById("acNotes").value.trim(),
  };
  if (!payload.username) return toast("Username wajib diisi", "warning");
  try {
    if (accountId) {
      await API.put(`/api/accounts/${accountId}`, payload);
      toast("Akun diperbarui ✓", "success");
    } else {
      // v1.46: kalau username SUDAH ada di HP lain, server otomatis
      // menambahkan PLACEMENT BARU di HP ini (akun ditempatkan di beberapa
      // HP sekaligus) — bukan menganggapnya akun baru terpisah. Tidak perlu
      // konfirmasi tambahan karena ini memang perilaku yang diinginkan.
      const res = await API.post("/api/accounts", payload);
      toast(
        res._placed_on_existing_account
          ? `Akun '${res.username}' sudah ada — kini juga ditempatkan di HP ini ✓ (riwayat tetap satu)`
          : "Akun ditambahkan ✓",
        "success", 5000,
      );
    }
    Modal.close();
    await loadDevices();
    // re-select kalau sedang edit akun terpilih
    if (accountId && state.selectedAccount?.id === accountId) {
      selectAccount(deviceId, accountId);
    }
  } catch (err) {
    toast(err.error || "Gagal menyimpan akun", "error");
  }
}

async function confirmDeleteAccount(account) {
  // v1.46: account dari sidebar hanya berisi 1 baris placement (HP saat ini
  // dibuka dari modal). Ambil detail lengkap dulu (termasuk daftar SEMUA
  // placement di HP lain) supaya dialog bisa menampilkan info yang akurat.
  let full = account;
  try {
    full = await API.get(`/api/accounts/${account.id}`);
  } catch (e) {
    /* fallback ke data seadanya bila gagal memuat detail */
  }

  // v1.46: akun bisa ditempatkan di banyak HP. Tawarkan 2 opsi jelas:
  // (1) lepas akun dari HP INI saja — akun & riwayatnya tetap ada di HP lain
  //     (atau tetap tersimpan sebagai akun "tanpa HP" bila ini placement
  //     terakhirnya), atau (2) hapus akun SEPENUHNYA dari semua HP sekaligus
  //     riwayatnya. Ini mencegah kehilangan data tidak sengaja saat akun
  //     yang sama masih dipakai di HP lain.
  const placements = full.placements || [];
  const otherPlacements = placements.filter((p) => p.device_id !== state.selectedDevice?.id);
  const hasOtherHp = otherPlacements.length > 0;

  Modal.open({
    title: "Hapus Akun?",
    bodyHtml: `<div style="font-size:13px;line-height:1.6">
      Akun <strong>${escapeHtml(account.username)}</strong>${
        hasOtherHp
          ? ` juga terdaftar di HP lain (${otherPlacements.map((p) => escapeHtml(p.device_name || "-")).join(", ")}).`
          : " hanya terdaftar di HP ini."
      }<br><br>
      <b>Lepas dari HP ini saja</b> — akun &amp; riwayatnya tetap ada${hasOtherHp ? " di HP lain" : ", tinggal ditempatkan lagi nanti"}.<br>
      <b>Hapus akun sepenuhnya</b> — akun &amp; SELURUH riwayat upload di semua HP ikut terhapus permanen.
    </div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: "📤 Lepas dari HP Ini Saja",
        class: "btn btn-secondary",
        onClick: async () => {
          try {
            const deviceId = state.selectedDevice?.id;
            await API.del(`/api/accounts/${account.id}/placements/${deviceId}`);
            toast("Akun dilepas dari HP ini (riwayat tetap aman)", "success");
            if (state.selectedAccount?.id === account.id) {
              state.selectedAccount = null;
              renderTopbar();
              renderAccountInfo();
            }
            Modal.close();
            await loadDevices();
          } catch (err) {
            toast(err.error || "Gagal melepas akun dari HP ini", "error");
          }
        },
      },
      {
        label: "🗑️ Hapus Akun Sepenuhnya",
        class: "btn btn-danger",
        onClick: async () => {
          try {
            await API.del(`/api/accounts/${account.id}`);
            toast("Akun dihapus sepenuhnya", "success");
            if (state.selectedAccount?.id === account.id) {
              state.selectedAccount = null;
              renderTopbar();
              renderAccountInfo();
            }
            Modal.close();
            await loadDevices();
          } catch (err) {
            toast(err.error || "Gagal menghapus akun", "error");
          }
        },
      },
    ],
  });
}

// ════════════════════════════════════════
// STATS (placeholder, diperkaya di v1.05)
// ════════════════════════════════════════
async function updateStats() {
  const onlineCount = state.devices.filter((d) => d.online === true).length;
  const hpOnlineEl = document.getElementById("statHpOnline");
  if (hpOnlineEl) hpOnlineEl.textContent = onlineCount;

  // Statistik dinamis dari DB
  try {
    const stats = await API.get("/api/history/stats");
    const uploadEl = document.getElementById("statUpload");
    const akunEl = document.getElementById("statAkun");
    const sesiEl = document.getElementById("statSisa");
    if (uploadEl) uploadEl.textContent = stats.upload_today;
    if (akunEl) akunEl.textContent = stats.accounts_done_today;
    if (sesiEl) sesiEl.textContent = stats.active_sessions;
  } catch (e) {
    /* biarkan default */
  }
}

// ════════════════════════════════════════
// PLACEHOLDER untuk halaman lain (diisi checkpoint berikutnya)
// ════════════════════════════════════════
// ════════════════════════════════════════
// DASHBOARD: RIWAYAT UPLOAD
// ════════════════════════════════════════
const History = {
  filterDeviceBound: false,
};

async function loadHistory() {
  // Isi dropdown filter HP & akun (sekali)
  await populateHistoryFilters();
  // Muat data dengan filter saat ini
  await fetchHistory();

  // Bind filter (sekali)
  if (!History.filterDeviceBound) {
    document.getElementById("filterDevice").onchange = onHistoryDeviceFilter;
    document.getElementById("filterAccount").onchange = fetchHistory;
    document.getElementById("filterDate").onchange = fetchHistory;
    document.getElementById("btnClearFilter").onclick = clearHistoryFilter;
    History.filterDeviceBound = true;
  }
}

async function populateHistoryFilters() {
  const devSel = document.getElementById("filterDevice");
  const accSel = document.getElementById("filterAccount");
  if (!devSel) return;

  // HP
  const currentDev = devSel.value;
  devSel.innerHTML = `<option value="">Semua HP</option>` +
    state.devices.map((d) => `<option value="${d.id}">${escapeHtml(d.name)}</option>`).join("");
  devSel.value = currentDev;

  // Akun (semua, atau sesuai HP terpilih)
  await refreshHistoryAccountOptions();
}

async function refreshHistoryAccountOptions() {
  const devSel = document.getElementById("filterDevice");
  const accSel = document.getElementById("filterAccount");
  const deviceId = devSel.value;

  let accounts = [];
  if (deviceId) {
    accounts = state.accounts[deviceId] || [];
  } else {
    // gabungkan semua akun
    Object.values(state.accounts).forEach((arr) => accounts.push(...arr));
  }
  const currentAcc = accSel.value;
  accSel.innerHTML = `<option value="">Semua Akun</option>` +
    accounts.map((a) => `<option value="${a.id}">${escapeHtml(a.username)}</option>`).join("");
  // pertahankan pilihan jika masih valid
  if ([...accSel.options].some((o) => o.value === currentAcc)) {
    accSel.value = currentAcc;
  }
}

async function onHistoryDeviceFilter() {
  await refreshHistoryAccountOptions();
  await fetchHistory();
}

async function fetchHistory() {
  const deviceId = document.getElementById("filterDevice").value;
  const accountId = document.getElementById("filterAccount").value;
  const date = document.getElementById("filterDate").value;

  const params = new URLSearchParams();
  if (deviceId) params.append("device_id", deviceId);
  if (accountId) params.append("account_id", accountId);
  if (date) params.append("date", date);

  try {
    const res = await API.get(`/api/history?${params.toString()}`);
    renderHistoryTable(res.sessions);
  } catch (err) {
    toast(err.error || "Gagal memuat riwayat", "error");
  }
}

function renderHistoryTable(sessions) {
  const tbody = document.getElementById("historyTableBody");
  const empty = document.getElementById("historyEmpty");
  if (!sessions || !sessions.length) {
    tbody.innerHTML = "";
    empty.style.display = "";
    return;
  }
  empty.style.display = "none";
  tbody.innerHTML = sessions
    .map((s) => {
      const when = formatDateTime(s.finished_at || s.started_at);
      const batch = s.batch_date
        ? `<span class="tag tag-blue">📅 ${escapeHtml(formatBatchDateShortApp(s.batch_date))}</span>`
        : `<span class="muted">—</span>`;
      const statusTag =
        s.status === "finished"
          ? `<span class="tag tag-green">✓ Selesai</span>`
          : `<span class="tag tag-gray">✕ Dibatalkan</span>`;
      const slotBadge = s.account_app_slot
        ? `<span class="slot-badge slot-${escapeHtml(s.account_app_slot)}">${(SLOT_ICON[s.account_app_slot] || "")} ${escapeHtml(SLOT_LABELS[s.account_app_slot] || s.account_app_slot)}</span>`
        : "";
      return `<tr data-session="${s.id}" style="cursor:pointer">
        <td class="mono">${escapeHtml(when)}</td>
        <td>${batch}</td>
        <td>${escapeHtml(s.device_name || "—")}</td>
        <td>${escapeHtml(s.account_username || "—")}${slotBadge ? "<br>" + slotBadge : ""}</td>
        <td class="mono">${escapeHtml(s.subfolder)}/</td>
        <td>${s.video_count} video</td>
        <td>${statusTag}</td>
      </tr>`;
    })
    .join("");

  tbody.querySelectorAll("[data-session]").forEach((row) => {
    row.onclick = () => showSessionDetail(+row.dataset.session);
  });
}

async function showSessionDetail(sessionId) {
  try {
    const res = await API.get(`/api/history/${sessionId}`);
    const s = res.session;
    const videos = res.videos;
    const when = formatDateTime(s.finished_at || s.started_at);
    Modal.open({
      title: `Detail Sesi #${sessionId}`,
      bodyHtml: `<div style="font-size:13px;line-height:1.7">
        <div class="flex" style="gap:24px;margin-bottom:12px;flex-wrap:wrap">
          <div><div class="muted" style="font-size:11px">Akun</div><div>${escapeHtml(s.account_username || "—")}</div></div>
          <div><div class="muted" style="font-size:11px">HP</div><div>${escapeHtml(s.device_name || "—")}</div></div>
          <div><div class="muted" style="font-size:11px">Subfolder</div><div class="mono">${escapeHtml(s.subfolder)}/</div></div>
          <div><div class="muted" style="font-size:11px">Tanggal Batch</div><div class="mono">${s.batch_date ? escapeHtml(s.batch_date) : "—"}</div></div>
          <div><div class="muted" style="font-size:11px">Waktu</div><div class="mono">${escapeHtml(when)}</div></div>
        </div>
        <div class="muted" style="font-size:12px;margin-bottom:6px">${videos.length} video diupload:</div>
        <div class="adb-console" style="color:var(--text);max-height:220px">
          ${videos.length
            ? videos.map((v) => `<div>✓ ${escapeHtml(v.filename)} <span class="muted" style="font-size:10px">— ${escapeHtml(formatDateTime(v.uploaded_at))}</span></div>`).join("")
            : '<div class="muted">Tidak ada video tercatat.</div>'}
        </div>
      </div>`,
      footerButtons: [{ label: "Tutup", class: "btn btn-ghost", onClick: Modal.close }],
    });
  } catch (err) {
    toast(err.error || "Gagal memuat detail", "error");
  }
}

function clearHistoryFilter() {
  document.getElementById("filterDevice").value = "";
  document.getElementById("filterAccount").value = "";
  document.getElementById("filterDate").value = "";
  refreshHistoryAccountOptions().then(fetchHistory);
}

// ── Riwayat terbaru di panel kanan halaman Upload ──
async function loadRecentHistory() {
  // Panel riwayat ringkas dihapus pada v1.23, tetapi fungsi ini tetap menjadi
  // hook refresh dari alur upload agar statistik Dashboard selalu mutakhir.
  if (typeof updateStats === "function") updateStats();
  const container = document.getElementById("recentHistory");
  if (!container) return;
  try {
    const res = await API.get("/api/history/recent?limit=5");
    const sessions = res.sessions || [];
    if (!sessions.length) {
      container.innerHTML = `<div class="muted" style="padding:14px;font-size:12px;text-align:center">Belum ada riwayat upload.</div>`;
      return;
    }
    container.innerHTML = sessions
      .map((s) => {
        const when = formatRelativeTime(s.finished_at);
        return `<div class="history-item">
          <div class="history-icon">✓</div>
          <div class="history-detail">
            <div class="history-akun">${escapeHtml(s.account_username || "—")}</div>
            <div class="history-meta">${s.video_count} video · ${escapeHtml(s.device_name || "—")} · folder ${escapeHtml(s.subfolder)}/</div>
          </div>
          <div class="history-time">${escapeHtml(when)}</div>
        </div>`;
      })
      .join("");
  } catch (err) {
    container.innerHTML = `<div class="muted" style="padding:14px;font-size:12px">Gagal memuat riwayat.</div>`;
  }
}

// ── Format tanggal/waktu helper ──
function formatDateTime(iso) {
  if (!iso) return "—";
  // SQLite simpan "YYYY-MM-DD HH:MM:SS" (UTC). Tampilkan ringkas.
  const d = parseSqlDate(iso);
  if (!d) return iso;
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatRelativeTime(iso) {
  if (!iso) return "—";
  const d = parseSqlDate(iso);
  if (!d) return "—";
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  const pad = (n) => String(n).padStart(2, "0");
  if (diffMin < 1) return "baru saja";
  if (diffMin < 60) return `${diffMin}m lalu`;
  // hari ini?
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  // kemarin?
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return "Kemarin";
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}`;
}

function parseSqlDate(iso) {
  // SQLite CURRENT_TIMESTAMP berupa UTC "YYYY-MM-DD HH:MM:SS"
  if (!iso) return null;
  const norm = iso.includes("T") ? iso : iso.replace(" ", "T") + "Z";
  const d = new Date(norm);
  return isNaN(d.getTime()) ? null : d;
}

// "YYYY-MM-DD" (tanggal batch v1.1.4) → "30/06/2026" — tanpa geser timezone
function formatBatchDateShortApp(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
  if (!m) return s || "—";
  return `${m[3]}/${m[2]}/${m[1]}`;
}
window.RemoteHPStoragePath = "";

async function loadSettings() {
  try {
    const s = await API.get("/api/settings");
    window.RemoteHPStoragePath = s.storage_path || "";
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val || "";
    };
    set("setRandomRange", s.random_range);
    set("setStoragePath", s.storage_path);
    set("setAdbPath", s.adb_path);
    set("setScrcpyPath", s.scrcpy_path);
    set("setScrcpyMode", s.scrcpy_mode || "stay_awake");
    set("setHpTargetDir", s.hp_target_dir);
  } catch (e) {
    /* abaikan; biarkan placeholder */
  }
  // Muat daftar template caption (v1.1.8)
  loadCaptionTemplates();
  // Muat mode koneksi USB/WiFi (v1.43)
  loadConnectionMode();
  loadAndroidPairing();
}

// ════════════════════════════════════════
// KONEKSI ADB USB / WI-FI (v1.50)
// ════════════════════════════════════════

function connectionLabel(d) {
  if (!d) return "Pilih HP untuk melihat status.";
  if (d.active_transport === "wifi") return `● Online via Wi-Fi — ${d.active_serial || d.wifi_endpoint || ""}`;
  if (d.active_transport === "usb") {
    const fallback = d.wifi_endpoint ? " · Wi-Fi tersimpan sebagai fallback" : "";
    return `● Online via USB — ${d.active_serial || d.usb_serial || ""}${fallback}`;
  }
  if (d.wifi_endpoint || d.usb_serial) return `○ Offline — ${d.wifi_endpoint ? "Wi-Fi " + d.wifi_endpoint : "USB " + d.usb_serial}`;
  return "○ Belum ada transport ADB yang dikonfigurasi.";
}

async function loadConnectionMode() {
  const statusEl = document.getElementById("connModeStatus");
  if (statusEl) {
    statusEl.textContent = "Koneksi dipilih otomatis per HP: Wi-Fi menjadi jalur utama saat tersedia dan USB menjadi fallback.";
  }
  await populateWifiDeviceSelects();
}

async function populateWifiDeviceSelects() {
  const usbSelect = document.getElementById("wifiUsbDeviceSelect");
  const connectSelect = document.getElementById("wifiConnectDeviceSelect");
  if (!usbSelect && !connectSelect) return;
  try {
    const devices = await API.get("/api/devices?check_status=1");
    const previousConnect = connectSelect?.value || "";
    const previousUsb = usbSelect?.value || "";
    const opts = (devices || [])
      .map((d) => `<option value="${d.id}">${escapeHtml(d.name || "HP #" + d.id)}${d.active_transport ? " · " + (d.active_transport === "wifi" ? "📶" : "🔌") : ""}</option>`)
      .join("");
    if (usbSelect) {
      usbSelect.innerHTML = opts || `<option value="">Belum ada HP terdaftar</option>`;
      if (previousUsb && [...usbSelect.options].some((o) => o.value === previousUsb)) usbSelect.value = previousUsb;
    }
    if (connectSelect) {
      connectSelect.innerHTML = opts || `<option value="">Belum ada HP terdaftar</option>`;
      if (previousConnect && [...connectSelect.options].some((o) => o.value === previousConnect)) connectSelect.value = previousConnect;
    }
    window.__wifiDevices = devices || [];
    updateWifiSelectedDeviceDetails();
  } catch (e) {
    const status = document.getElementById("wifiSelectedStatus");
    if (status) status.textContent = e.error || "Gagal memuat status HP";
  }
}

function updateWifiSelectedDeviceDetails() {
  const select = document.getElementById("wifiConnectDeviceSelect");
  const deviceId = +(select?.value || 0);
  const d = (window.__wifiDevices || []).find((item) => +item.id === deviceId);
  const status = document.getElementById("wifiSelectedStatus");
  const endpoint = document.getElementById("wifiConnectIpPort");
  const pref = document.getElementById("wifiPreferredTransport");
  const auto = document.getElementById("wifiAutoReconnect");
  if (status) status.textContent = connectionLabel(d);
  if (endpoint && d?.wifi_endpoint) endpoint.value = d.wifi_endpoint;
  if (pref) pref.value = d?.preferred_transport || "auto";
  if (auto) auto.checked = d?.wifi_auto_reconnect !== false && d?.wifi_auto_reconnect !== 0;
}

(function bindConnectionButtonsV149() {
  const connectSelect = document.getElementById("wifiConnectDeviceSelect");
  if (connectSelect) connectSelect.onchange = updateWifiSelectedDeviceDetails;

  const btnEnableFromUsb = document.getElementById("btnWifiEnableFromUsb");
  if (btnEnableFromUsb) {
    btnEnableFromUsb.onclick = async () => {
      const deviceId = document.getElementById("wifiUsbDeviceSelect")?.value;
      const ip = document.getElementById("wifiUsbIpOverride")?.value?.trim();
      if (!deviceId) return toast("Pilih HP yang sedang terhubung USB", "warning");
      btnEnableFromUsb.disabled = true;
      btnEnableFromUsb.textContent = "⏳ Mengaktifkan...";
      try {
        const res = await API.post(`/api/devices/${deviceId}/wifi/enable-from-usb`, ip ? { ip } : {});
        toast(`Wi-Fi ADB aktif: ${res.ip_port}. Kabel USB boleh dicabut.`, "success", 6000);
        await loadDevices(true);
        await populateWifiDeviceSelects();
      } catch (err) {
        toast(err.error || "Gagal mengaktifkan Wi-Fi dari USB", "error", 6000);
      } finally {
        btnEnableFromUsb.disabled = false;
        btnEnableFromUsb.textContent = "⚡ Aktifkan Wi-Fi dari USB";
      }
    };
  }

  const btnPair = document.getElementById("btnWifiPair");
  if (btnPair) {
    btnPair.onclick = async () => {
      const pairingIpPort = document.getElementById("wifiPairIpPort")?.value?.trim();
      const pairingCode = document.getElementById("wifiPairCode")?.value?.trim();
      if (!pairingIpPort || !pairingCode) return toast("Isi IP:Port pairing dan kode 6 digit dari HP", "warning");
      btnPair.disabled = true;
      btnPair.textContent = "⏳ Memasangkan...";
      try {
        await API.post("/api/devices/wifi/pair", { pairing_ip_port: pairingIpPort, pairing_code: pairingCode });
        toast("Pairing berhasil. Sekarang masukkan IP:Port koneksi dan hubungkan ke HP yang dipilih.", "success", 6500);
      } catch (err) {
        toast(err.error || "Pairing gagal", "error", 6000);
      } finally {
        btnPair.disabled = false;
        btnPair.textContent = "🔗 Pasangkan";
      }
    };
  }

  const btnConnect = document.getElementById("btnWifiConnect");
  if (btnConnect) {
    btnConnect.onclick = async () => {
      const deviceId = document.getElementById("wifiConnectDeviceSelect")?.value;
      const ipPort = document.getElementById("wifiConnectIpPort")?.value?.trim();
      if (!deviceId) return toast("Pilih HP tujuan", "warning");
      if (!ipPort) return toast("Isi IP:Port koneksi Wireless Debugging", "warning");
      btnConnect.disabled = true;
      btnConnect.textContent = "⏳ Menghubungkan...";
      try {
        await API.post(`/api/devices/${deviceId}/wifi/connect`, { ip_port: ipPort });
        toast("HP terhubung via Wi-Fi dan endpoint disimpan ✓", "success");
        await loadDevices(true);
        await populateWifiDeviceSelects();
      } catch (err) {
        toast(err.error || "Gagal terhubung via Wi-Fi", "error", 6000);
      } finally {
        btnConnect.disabled = false;
        btnConnect.textContent = "📶 Hubungkan & Simpan";
      }
    };
  }

  const btnReconnect = document.getElementById("btnWifiReconnect");
  if (btnReconnect) {
    btnReconnect.onclick = async () => {
      const deviceId = document.getElementById("wifiConnectDeviceSelect")?.value;
      if (!deviceId) return toast("Pilih HP tujuan", "warning");
      try {
        await API.post(`/api/devices/${deviceId}/wifi/reconnect`, {});
        toast("Reconnect Wi-Fi berhasil ✓", "success");
        await loadDevices(true);
        await populateWifiDeviceSelects();
      } catch (err) {
        toast(err.error || "Reconnect gagal", "error", 6000);
      }
    };
  }

  const btnDisconnect = document.getElementById("btnWifiDisconnect");
  if (btnDisconnect) {
    btnDisconnect.onclick = async () => {
      const deviceId = document.getElementById("wifiConnectDeviceSelect")?.value;
      if (!deviceId) return toast("Pilih HP tujuan", "warning");
      try {
        await API.post(`/api/devices/${deviceId}/wifi/disconnect`, {});
        toast("Koneksi Wi-Fi diputus. Data pairing/endpoint tetap disimpan.", "info");
        await loadDevices(true);
        await populateWifiDeviceSelects();
      } catch (err) {
        toast(err.error || "Gagal memutus Wi-Fi", "error");
      }
    };
  }

  const btnSave = document.getElementById("btnWifiSavePreference");
  if (btnSave) {
    btnSave.onclick = async () => {
      const deviceId = document.getElementById("wifiConnectDeviceSelect")?.value;
      if (!deviceId) return toast("Pilih HP tujuan", "warning");
      const preferredTransport = document.getElementById("wifiPreferredTransport")?.value || "auto";
      const wifiAutoReconnect = !!document.getElementById("wifiAutoReconnect")?.checked;
      try {
        await API.post(`/api/devices/${deviceId}/connection-preference`, {
          preferred_transport: preferredTransport,
          wifi_auto_reconnect: wifiAutoReconnect,
        });
        toast("Preferensi koneksi disimpan ✓", "success");
        await loadDevices(true);
        await populateWifiDeviceSelects();
      } catch (err) {
        toast(err.error || "Gagal menyimpan preferensi", "error");
      }
    };
  }
})();

// ════════════════════════════════════════
// TEMPLATE CAPTION (v1.1.8)
// ════════════════════════════════════════
async function loadCaptionTemplates() {
  const box = document.getElementById("captionTemplateList");
  if (!box) return;
  const countLabel = document.getElementById("captionCountLabel");
  const countBar = document.getElementById("captionCountBar");
  try {
    const res = await API.get("/api/settings/captions");
    const templates = res.templates || [];
    if (countLabel) countLabel.textContent = templates.length ? `${templates.length} template caption` : "";
    if (countBar) countBar.style.display = templates.length ? "flex" : "none";
    if (!templates.length) {
      box.innerHTML = `<div class="muted" style="font-size:12.5px;padding:8px 0">Belum ada template. Klik "📄 Unggah File" untuk mengunggah banyak sekaligus, atau "+ Tambah" untuk menambah satu per satu.</div>`;
      return;
    }
    box.innerHTML = templates
      .map((t) => {
        const tags = (t.hashtags || "").trim();
        const active = t.is_active ? "" : "opacity:.5";
        return `<div class="caption-tpl" style="${active}">
          <div class="caption-tpl-main">
            <div class="caption-tpl-text">${escapeHtml(t.content || "")}</div>
            ${tags ? `<div class="caption-tpl-tags">${escapeHtml(tags)}</div>` : ""}
          </div>
          <div class="caption-tpl-actions">
            <button class="btn btn-ghost icon-btn" data-cap-edit="${t.id}">✏️</button>
            <button class="btn btn-danger icon-btn" data-cap-del="${t.id}">🗑️</button>
          </div>
        </div>`;
      })
      .join("");
    box.querySelectorAll("[data-cap-edit]").forEach((b) => {
      const t = templates.find((x) => x.id === +b.dataset.capEdit);
      b.onclick = () => openCaptionModal(t);
    });
    box.querySelectorAll("[data-cap-del]").forEach((b) => {
      b.onclick = () => confirmDeleteCaption(+b.dataset.capDel);
    });
  } catch (err) {
    box.innerHTML = `<div class="muted" style="font-size:12.5px">Gagal memuat template caption.</div>`;
  }
}

// Buka dialog unggah file caption (.md/.txt)
function openCaptionUploadModal() {
  Modal.open({
    title: "📄 Unggah File Caption",
    bodyHtml: `
      <div style="font-size:12.5px;line-height:1.7;color:var(--muted);margin-bottom:12px">
        Unggah file <b>.md</b> atau <b>.txt</b> berisi banyak caption sekaligus.
        <div style="background:var(--surface-2,#1a1a1a);border:1px solid var(--border);border-radius:8px;padding:10px;margin-top:8px;font-family:monospace;font-size:11.5px;white-space:pre-wrap">Caption pertama di sini
#fyp #tips

Caption kedua di sini
#fyp #relatable</div>
        <div style="margin-top:8px">Aturannya sederhana: <b>pisahkan tiap caption dengan satu baris kosong</b>. Baris yang diawali <code>#</code> otomatis jadi hashtag. Format markdown (heading, bullet <code>-</code>, garis <code>---</code>) juga didukung.</div>
      </div>
      <div class="form-group">
        <label class="form-label">Pilih file</label>
        <button type="button" class="btn btn-ghost" id="capUploadPickBtn" style="width:100%">📁 Pilih file .md / .txt…</button>
        <div class="muted" id="capUploadFileName" style="font-size:12px;margin-top:6px">Belum ada file dipilih.</div>
      </div>
      <div class="form-group">
        <label class="form-label">Mode</label>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;margin-bottom:6px">
          <input type="radio" name="capUploadMode" value="append" checked> Tambahkan ke daftar yang sudah ada
        </label>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer">
          <input type="radio" name="capUploadMode" value="replace"> Ganti semua (hapus lama, pakai file ini saja)
        </label>
      </div>
      <div id="capUploadPreview" class="muted" style="font-size:12px;margin-top:4px"></div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      { label: "Unggah", class: "btn btn-primary", id: "capUploadSubmitBtn", onClick: submitCaptionUpload },
    ],
  });

  // state file terpilih
  _captionUploadText = null;
  const pickBtn = document.getElementById("capUploadPickBtn");
  const fileInput = document.getElementById("captionFileInput");
  const nameLabel = document.getElementById("capUploadFileName");
  const preview = document.getElementById("capUploadPreview");

  pickBtn.onclick = () => fileInput.click();
  fileInput.onchange = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (file.size > 1024 * 1024) {
      toast("File terlalu besar (maksimal 1 MB)", "error");
      fileInput.value = "";
      return;
    }
    try {
      const text = await file.text();
      _captionUploadText = text;
      nameLabel.textContent = `✓ ${file.name} (${Math.max(1, Math.round(file.size / 1024))} KB)`;
      // pratinjau jumlah caption terbaca (hitung blok dipisah baris kosong, kasar)
      const blocks = text.split(/\n\s*\n/).filter((b) => b.trim() && !/^#{1,6}\s+\S+$/.test(b.trim()));
      preview.textContent = `Perkiraan ${blocks.length} caption akan diproses. Klik Unggah untuk memasukkan.`;
    } catch (err) {
      toast("Gagal membaca file", "error");
    }
    fileInput.value = "";
  };
}

let _captionUploadText = null;

async function submitCaptionUpload() {
  if (!_captionUploadText || !_captionUploadText.trim()) {
    return toast("Pilih file dulu", "warning");
  }
  const mode = (document.querySelector('input[name="capUploadMode"]:checked') || {}).value || "append";
  const btn = document.getElementById("capUploadSubmitBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Mengunggah…"; }
  try {
    const res = await API.post("/api/settings/captions/upload", { text: _captionUploadText, mode });
    let msg = `Berhasil: ${res.added} caption ditambahkan`;
    if (mode === "replace" && res.replaced) msg += ` (${res.replaced} lama diganti)`;
    if (res.skipped_empty) msg += `, ${res.skipped_empty} blok kosong dilewati`;
    toast(msg, "success", 6000);
    if (res.risky_count) {
      toast(`⚠️ ${res.risky_count} caption mungkin mengandung frasa over-claim — cek & edit bila perlu`, "warning", 8000);
    }
    Modal.close();
    _captionUploadText = null;
    await loadCaptionTemplates();
  } catch (err) {
    toast(err.error || "Gagal mengunggah file", "error", 6000);
    if (btn) { btn.disabled = false; btn.textContent = "Unggah"; }
  }
}

function confirmDeleteAllCaptions() {
  Modal.open({
    title: "Hapus Semua Template Caption?",
    bodyHtml: `<div style="font-size:13px;line-height:1.6">Yakin ingin menghapus <b>SEMUA</b> template caption?<br><span class="muted">Tindakan ini tidak bisa dibatalkan. Cocok dipakai kalau mau mulai bersih sebelum mengunggah file baru.</span></div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: "Ya, Hapus Semua", class: "btn btn-danger",
        onClick: async () => {
          try {
            const res = await API.del("/api/settings/captions/all");
            toast(`${res.deleted} caption dihapus`, "success");
            Modal.close();
            await loadCaptionTemplates();
          } catch (err) {
            toast(err.error || "Gagal menghapus", "error");
          }
        },
      },
    ],
  });
}

// Ringkasan peringatan risiko → HTML
function captionRiskHtml(check) {
  if (!check || !check.risky) return "";
  const phrases = (check.matches || []).map((m) => `"${escapeHtml(m.phrase)}"`).join(", ");
  const cats = (check.categories || []).map(escapeHtml).join(", ");
  return `<div class="caption-warn" id="captionWarn">
    ⚠️ <b>Peringatan:</b> caption ini mengandung frasa yang berpotensi over-claim/ajakan langsung.
    <div style="margin-top:4px">Terdeteksi (${escapeHtml(cats)}): ${phrases}</div>
    <div class="muted" style="margin-top:4px;font-size:11px">Ini hanya peringatan — Anda tetap bisa menyimpan. Pertimbangkan gaya yang lebih netral.</div>
  </div>`;
}

let _captionCheckTimer = null;
function openCaptionModal(tpl = null) {
  const isEdit = !!tpl;
  Modal.open({
    title: isEdit ? "Edit Template Caption" : "Tambah Template Caption",
    bodyHtml: `
      <div class="form-group">
        <label class="form-label">Isi Caption *</label>
        <textarea class="input" id="capContent" style="min-height:90px" placeholder="Tulis caption yang natural, tanpa klaim berlebihan...">${escapeHtml(
          tpl?.content || ""
        )}</textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Hashtag (maks. 3 yang dipakai saat posting)</label>
        <input class="input" id="capHashtags" value="${escapeHtml(tpl?.hashtags || "")}" placeholder="#fyp #relatable #tips">
        <span class="muted" style="font-size:11.5px">Boleh isi lebih, tapi saat generate hanya 3 (acak) yang dipakai.</span>
      </div>
      <div id="capWarnSlot"></div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: isEdit ? "Simpan" : "Tambah",
        class: "btn btn-primary",
        onClick: () => saveCaption(tpl?.id),
      },
    ],
  });

  // Cek risiko live saat mengetik (debounce), tampil di slot peringatan.
  const run = () => {
    const content = document.getElementById("capContent").value;
    const hashtags = document.getElementById("capHashtags").value;
    clearTimeout(_captionCheckTimer);
    _captionCheckTimer = setTimeout(async () => {
      try {
        const res = await API.post("/api/settings/captions/check", { content, hashtags });
        document.getElementById("capWarnSlot").innerHTML = captionRiskHtml(res.check);
      } catch (e) {
        /* diamkan */
      }
    }, 350);
  };
  document.getElementById("capContent").addEventListener("input", run);
  document.getElementById("capHashtags").addEventListener("input", run);
  run(); // cek awal (berguna saat edit template lama yang mungkin berisiko)
}

async function saveCaption(tplId) {
  const content = document.getElementById("capContent").value.trim();
  const hashtags = document.getElementById("capHashtags").value.trim();
  if (!content) return toast("Isi caption tidak boleh kosong", "warning");
  try {
    let res;
    if (tplId) {
      res = await API.put(`/api/settings/captions/${tplId}`, { content, hashtags });
    } else {
      res = await API.post("/api/settings/captions", { content, hashtags });
    }
    // Tampilkan peringatan bila server menandai berisiko (tetap tersimpan).
    if (res.check && res.check.risky) {
      const cats = (res.check.categories || []).join(", ");
      const phrases = (res.check.matches || []).map((m) => `"${m.phrase}"`).join(", ");
      toast(`Tersimpan, tapi ada frasa berisiko (${cats}): ${phrases}`, "warning", 7000);
    } else {
      toast(tplId ? "Template diperbarui ✓" : "Template ditambahkan ✓", "success");
    }
    Modal.close();
    loadCaptionTemplates();
  } catch (err) {
    toast(err.error || "Gagal menyimpan template", "error");
  }
}

function confirmDeleteCaption(tplId) {
  Modal.open({
    title: "Hapus Template?",
    bodyHtml: `<div style="font-size:13px;line-height:1.6">Yakin hapus template caption ini?<br><span class="muted">Tindakan ini tidak bisa dibatalkan.</span></div>`,
    footerButtons: [
      { label: "Batal", class: "btn btn-ghost", onClick: Modal.close },
      {
        label: "Ya, Hapus",
        class: "btn btn-danger",
        onClick: async () => {
          try {
            await API.del(`/api/settings/captions/${tplId}`);
            toast("Template dihapus", "success");
            Modal.close();
            loadCaptionTemplates();
          } catch (err) {
            toast(err.error || "Gagal menghapus", "error");
          }
        },
      },
    ],
  });
}

// ════════════════════════════════════════
// INIT
// ════════════════════════════════════════
document.getElementById("btnAddHp").onclick = () => openDeviceModal();
document.getElementById("btnRefreshHp").onclick = async () => {
  const icon = document.getElementById("btnRefreshHp");
  icon.textContent = "⏳";
  try {
    const status = await API.get("/api/devices/status");
    if (!status.adb_available) {
      toast("ADB tidak terdeteksi. Set path di Pengaturan atau install ADB.", "warning", 5000);
    }
    await loadDevices(true);
    const onlineCount = state.devices.filter((d) => d.online === true).length;
    if (status.adb_available) {
      toast(`Status diperbarui — ${onlineCount} HP online`, "success");
    }
  } catch (err) {
    toast(err.error || "Gagal cek status HP", "error");
  } finally {
    icon.textContent = "🔄";
  }
};

loadDevices();
loadRecentHistory();
loadSettings();

const btnRefreshDashboard = document.getElementById("btnRefreshDashboard");
if (btnRefreshDashboard) {
  btnRefreshDashboard.onclick = async () => {
    btnRefreshDashboard.disabled = true;
    const original = btnRefreshDashboard.textContent;
    btnRefreshDashboard.textContent = "⏳ Memuat";
    try {
      await loadDevices(true);
      await updateStats();
      toast("Dashboard diperbarui ✓", "success", 1800);
    } catch (err) {
      toast(err.error || "Gagal memperbarui dashboard", "error");
    } finally {
      btnRefreshDashboard.disabled = false;
      btnRefreshDashboard.textContent = original;
    }
  };
}

// Sidebar responsif: pada layar kecil menjadi drawer agar panel utama tetap lega.
const sidebarToggle = document.getElementById("sidebarToggle");
const sidebarBackdrop = document.getElementById("sidebarBackdrop");
function closeSidebarOnCompact() {
  document.body.classList.remove("sidebar-open");
  if (sidebarToggle) sidebarToggle.setAttribute("aria-expanded", "false");
}
if (sidebarToggle) {
  sidebarToggle.onclick = () => {
    const isOpen = document.body.classList.toggle("sidebar-open");
    sidebarToggle.setAttribute("aria-expanded", String(isOpen));
  };
}
if (sidebarBackdrop) sidebarBackdrop.onclick = closeSidebarOnCompact;
window.addEventListener("resize", () => {
  if (!window.matchMedia("(max-width: 900px)").matches) closeSidebarOnCompact();
});

// ── Tombol Simpan Pengaturan & Backup Database ──
(function bindSettingsButtons() {
  const saveSettings = async (triggerButton) => {
    const get = (id) => (document.getElementById(id)?.value || "").trim();
    const saveButtons = [
      document.getElementById("btnSaveSettings"),
      document.getElementById("btnSaveSettingsBottom"),
    ].filter(Boolean);
    saveButtons.forEach((button) => { button.disabled = true; });
    if (triggerButton) triggerButton.textContent = "⏳ Menyimpan...";
    try {
      await API.post("/api/settings", {
        random_range: get("setRandomRange"),
        storage_path: get("setStoragePath"),
        adb_path: get("setAdbPath"),
        scrcpy_path: get("setScrcpyPath"),
        scrcpy_mode: get("setScrcpyMode") || "stay_awake",
        hp_target_dir: get("setHpTargetDir"),
      });
      await loadSettings();
      if (typeof Upload !== "undefined") {
        Upload.videoSources = [];
        Upload.folderPath = null;
        Upload.scanResult = null;
        Upload.sourceRoot = window.RemoteHPStoragePath || null;
      }
      toast("Pengaturan tersimpan ✓", "success");
    } catch (err) {
      toast(err.error || "Gagal menyimpan pengaturan", "error");
    } finally {
      saveButtons.forEach((button) => {
        button.disabled = false;
        button.textContent = "💾 Simpan Pengaturan";
      });
    }
  };

  ["btnSaveSettings", "btnSaveSettingsBottom"].forEach((id) => {
    const button = document.getElementById(id);
    if (button) button.onclick = () => saveSettings(button);
  });
  const btnBackup = document.getElementById("btnBackupDb");
  if (btnBackup) {
    btnBackup.onclick = () => {
      // Unduh file database langsung
      window.location.href = "/api/settings/backup-db";
    };
  }
  // v1.1.8 — tombol tambah template caption
  const btnAddCap = document.getElementById("btnAddCaption");
  if (btnAddCap) {
    btnAddCap.onclick = () => openCaptionModal();
  }
  // v1.1.17 — tombol unggah file caption & hapus semua
  const btnUploadCap = document.getElementById("btnUploadCaptions");
  if (btnUploadCap) {
    btnUploadCap.onclick = () => openCaptionUploadModal();
  }
  const btnDeleteAllCap = document.getElementById("btnDeleteAllCaptions");
  if (btnDeleteAllCap) {
    btnDeleteAllCap.onclick = () => confirmDeleteAllCaptions();
  }
})();


// ════════════════════════════════════════
// ANDROID CONTROLLER PAIRING (v1.50)
// ════════════════════════════════════════
async function loadAndroidPairing() {
  const rowsEl = document.getElementById("androidClientRows");
  const selectEl = document.getElementById("androidPairDevice");
  if (!rowsEl && !selectEl) return;
  try {
    const data = await API.get("/api/pairing");
    const devices = Array.isArray(data.devices) ? data.devices : [];
    if (selectEl) {
      const old = selectEl.value;
      selectEl.innerHTML = devices.map((d) => `<option value="${d.id}">${escapeHtml(d.name || "HP #" + d.id)}</option>`).join("") || `<option value="">Belum ada HP</option>`;
      if (old && [...selectEl.options].some((o) => o.value === old)) selectEl.value = old;
    }
    const lan = document.getElementById("androidLanUrl");
    if (lan) lan.textContent = `Alamat LAN PC: ${data.lan_server_url || "—"} · gunakan jalankan-windows-lan.bat saat memakai Android.`;
    const cacheStatus = document.getElementById("androidCacheStatus");
    if (cacheStatus) {
      const cache = data.setup_cache || {};
      cacheStatus.textContent = cache.cached_at
        ? `Cache video Android: ${cache.ready_collections || 0} sumber READY · ${cache.cached_at}`
        : "Cache setup Android belum dibuat. Klik Refresh Cache Video Android setelah sumber video siap.";
    }
    if (rowsEl) {
      const clients = Array.isArray(data.clients) ? data.clients : [];
      rowsEl.innerHTML = clients.map((c) => {
        const active = c.status === "active";
        return `<tr>
          <td><span class="badge ${active ? "active" : "revoked"}">${active ? "Aktif" : "Dicabut"}</span></td>
          <td><strong>${escapeHtml(c.display_name || "Android")}</strong><small>${escapeHtml(c.token_prefix || "")}</small></td>
          <td>${escapeHtml(c.device_name || "—")}</td>
          <td>${escapeHtml(c.app_version || "—")}</td>
          <td>${escapeHtml(c.last_seen_at || c.paired_at || "—")}</td>
          <td>${active ? `<button class="btn btn-danger btn-sm" onclick="revokeAndroidClient(${c.id})">Revoke</button>` : "—"}</td>
        </tr>`;
      }).join("") || `<tr><td colspan="6" class="empty">Belum ada Android Controller yang dipasangkan.</td></tr>`;
    }
  } catch (err) {
    if (rowsEl) rowsEl.innerHTML = `<tr><td colspan="6" class="empty">${escapeHtml(err.error || "Gagal memuat pairing Android")}</td></tr>`;
  }
}


async function refreshAndroidSetupCache() {
  const btn = document.getElementById("btnAndroidCacheRefresh");
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Memindai dari PC..."; }
  try {
    const res = await API.post("/api/pairing/setup-cache/refresh", {});
    const ready = (res.collections || []).filter((row) => row.available).length;
    toast(`Cache Android diperbarui: ${ready} sumber memiliki batch READY.`, "success", 5000);
    await loadAndroidPairing();
  } catch (err) {
    toast(err.error || "Gagal memperbarui cache video Android", "error", 6000);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "↻ Refresh Cache Video Android"; }
  }
}

async function createAndroidPairing() {
  const deviceId = +(document.getElementById("androidPairDevice")?.value || 0);
  const expires = +(document.getElementById("androidPairExpiry")?.value || 10);
  if (!deviceId) return toast("Pilih HP yang akan dipasangkan", "warning");
  const btn = document.getElementById("btnAndroidPairCode");
  if (btn) { btn.disabled = true; btn.textContent = "⏳ Membuat..."; }
  try {
    const res = await API.post("/api/pairing/codes", { device_id: deviceId, expires_minutes: expires });
    const p = res.pairing || {};
    const box = document.getElementById("androidPairResult");
    if (box) {
      box.style.display = "block";
      box.innerHTML = `<div class="connection-summary-box"><strong>Pairing untuk ${escapeHtml(p.device_name || "HP")}</strong>
        <span>Server: <b>${escapeHtml(p.server_url || "—")}</b> · kode berlaku ${expires} menit.</span></div>
        <div class="wifi-setup-row" style="align-items:flex-start;margin-top:12px">
          ${p.qr_data_uri ? `<img src="${p.qr_data_uri}" alt="QR pairing" style="width:190px;height:190px;background:#fff;padding:8px;border-radius:12px">` : ""}
          <div><div class="form-label">Kode manual</div><div class="mono" style="font-size:28px;font-weight:800;letter-spacing:2px">${escapeHtml(p.code || "")}</div>
          <div class="field-help" style="margin-top:8px">Scan QR memakai kamera Android lalu pilih Remote HP, atau masukkan server dan kode secara manual di aplikasi Android.</div></div>
        </div>`;
    }
    toast("QR pairing dibuat. Kode hanya dapat digunakan satu kali.", "success", 5000);
    await loadAndroidPairing();
  } catch (err) {
    toast(err.error || "Gagal membuat pairing Android", "error", 6000);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "＋ Buat QR Pairing"; }
  }
}

async function revokeAndroidClient(clientId) {
  try {
    await API.post(`/api/pairing/clients/${clientId}/revoke`, {});
    toast("Akses Android Controller dicabut", "success");
    await loadAndroidPairing();
  } catch (err) { toast(err.error || "Gagal revoke Android", "error"); }
}
window.revokeAndroidClient = revokeAndroidClient;

(function bindAndroidControllerV150() {
  const create = document.getElementById("btnAndroidPairCode");
  if (create) create.onclick = createAndroidPairing;
  const refresh = document.getElementById("btnAndroidRefresh");
  if (refresh) refresh.onclick = loadAndroidPairing;
  const cache = document.getElementById("btnAndroidCacheRefresh");
  if (cache) cache.onclick = refreshAndroidSetupCache;
})();
