const form = document.getElementById("activationForm");
const input = document.getElementById("activationCode");
const button = document.getElementById("activateButton");
const retryButton = document.getElementById("retryButton");
const errorBox = document.getElementById("activationError");
const statusPill = document.getElementById("activationStatus");
const message = document.getElementById("activationMessage");

function showError(text) {
  errorBox.textContent = text || "Terjadi kesalahan.";
  errorBox.hidden = false;
}

function setBusy(busy, text) {
  button.disabled = busy;
  retryButton.disabled = busy;
  button.textContent = busy ? (text || "Menghubungkan…") : "Aktifkan Video Mixer";
}

function renderStatus(data) {
  statusPill.textContent = data.message || data.status;
  statusPill.dataset.status = data.status;
  message.textContent = data.message || "Masukkan kode aktivasi dari admin Remote Server.";
  form.hidden = !!data.activated;
  retryButton.hidden = !data.activated;
  if (data.allowed) window.location.replace("/");
}

async function getStatus() {
  try {
    const response = await fetch("/api/remote-auth/status", { cache: "no-store" });
    renderStatus(await response.json());
  } catch (_) {
    statusPill.textContent = "Aplikasi lokal belum siap.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  const code = input.value.trim().toUpperCase();
  if (!code) return showError("Masukkan kode aktivasi.");
  setBusy(true, "Mengaktifkan…");
  try {
    const response = await fetch("/api/remote-auth/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Aktivasi gagal.");
    window.location.replace("/");
  } catch (error) {
    showError(error.message);
    await getStatus();
  } finally {
    setBusy(false);
  }
});

retryButton.addEventListener("click", async () => {
  errorBox.hidden = true;
  setBusy(true, "Menghubungkan…");
  try {
    const response = await fetch("/api/remote-auth/retry", { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || data.message || "Koneksi gagal.");
    window.location.replace("/");
  } catch (error) {
    showError(error.message);
    await getStatus();
  } finally {
    setBusy(false);
  }
});

getStatus();
setInterval(getStatus, 5000);
