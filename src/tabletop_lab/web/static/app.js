function formatSeconds(value) {
  if (!Number.isFinite(value)) return "";
  if (value < 60) return `${value.toFixed(1)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}

async function updateRunProgress(panel) {
  const runId = panel.dataset.runId;
  const response = await fetch(`/runs/${runId}/status`);
  if (!response.ok) return;
  const status = await response.json();
  const bar = panel.querySelector(".progress-bar");
  const text = panel.querySelector(".progress-text");
  const elapsed = panel.querySelector('[data-field="elapsed"]');
  const gps = panel.querySelector('[data-field="gps"]');
  const eta = panel.querySelector('[data-field="eta"]');

  if (bar) bar.style.width = `${status.percent}%`;
  if (text) text.textContent = `${status.completed} / ${status.total} games (${status.percent.toFixed(1)}%)`;
  if (elapsed) elapsed.textContent = formatSeconds(status.elapsed_seconds);
  if (gps) gps.textContent = status.games_per_second ? status.games_per_second.toFixed(1) : "";
  if (eta) eta.textContent = status.status === "running" ? formatSeconds(status.eta_seconds) : "";

  if (status.status === "complete" || status.status === "failed") {
    window.location.reload();
    return;
  }
  window.setTimeout(() => updateRunProgress(panel), 800);
}

document.querySelectorAll("[data-run-id]").forEach((panel) => {
  updateRunProgress(panel);
});
