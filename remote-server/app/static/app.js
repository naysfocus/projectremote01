"use strict";

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-copy-value]");
  if (!target) return;
  const value = target.getAttribute("data-copy-value") || "";
  if (!value) return;
  const original = target.textContent;
  try {
    await navigator.clipboard.writeText(value);
    target.textContent = "Tersalin";
  } catch (_error) {
    const input = document.createElement("textarea");
    input.value = value;
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    document.execCommand("copy");
    input.remove();
    target.textContent = "Tersalin";
  }
  window.setTimeout(() => { target.textContent = original; }, 1500);
});
