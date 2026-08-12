(function () {
  let overlay = null;
  let banner = null;

  function ensureUi() {
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "remote-auth-banner";
      document.body.appendChild(banner);
    }
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "remote-auth-overlay";
      overlay.innerHTML = `<div class="remote-auth-dialog">
        <div class="remote-auth-icon">🔒</div>
        <h2>Video Mixer tidak dapat digunakan</h2>
        <p id="remoteAuthOverlayMessage"></p>
        <button id="remoteAuthRetry" class="btn primary">Coba hubungkan kembali</button>
      </div>`;
      document.body.appendChild(overlay);
      overlay.querySelector("#remoteAuthRetry").onclick = retry;
    }
  }

  async function retry() {
    const button = overlay.querySelector("#remoteAuthRetry");
    button.disabled = true;
    button.textContent = "Menghubungkan…";
    try {
      await fetch("/api/remote-auth/retry", { method: "POST" });
      await poll();
    } finally {
      button.disabled = false;
      button.textContent = "Coba hubungkan kembali";
    }
  }

  function render(data) {
    ensureUi();
    const grace = data.status === "grace";
    banner.classList.toggle("show", grace);
    banner.textContent = grace ? data.message : "";
    const blocked = !data.allowed;
    overlay.classList.toggle("show", blocked);
    if (blocked) {
      overlay.querySelector("#remoteAuthOverlayMessage").textContent = data.message || "Hubungi admin Remote Server.";
    }
  }

  async function poll() {
    try {
      const response = await fetch("/api/remote-auth/status", { cache: "no-store" });
      render(await response.json());
    } catch (_) {
      render({ allowed: false, status: "offline_blocked", message: "Status Remote Server tidak dapat diperiksa." });
    }
  }

  ensureUi();
  poll();
  setInterval(poll, 10000);
})();
