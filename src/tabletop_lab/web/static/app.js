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
  applyRunStatus(panel, status);

  if (status.status === "complete" || status.status === "failed") {
    const form = document.querySelector("[data-run-form]");
    if (form) setRunFormDisabled(form, false);
    return;
  }
  window.setTimeout(() => updateRunProgress(panel), 800);
}

function applyRunStatus(panel, status) {
  const bar = panel.querySelector(".progress-bar");
  const text = panel.querySelector(".progress-text");
  const elapsed = panel.querySelector('[data-field="elapsed"]');
  const gps = panel.querySelector('[data-field="gps"]');
  const eta = panel.querySelector('[data-field="eta"]');
  const statusLabel = panel.querySelector('[data-field="status"]');
  const detailLink = panel.querySelector('[data-field="detail-link"]');

  if (bar) bar.style.width = `${status.percent}%`;
  if (text) text.textContent = `${status.progress_completed} / ${status.progress_total} games (${status.percent.toFixed(1)}%)`;
  if (elapsed) elapsed.textContent = formatSeconds(status.elapsed_seconds);
  if (gps) gps.textContent = status.games_per_second ? status.games_per_second.toFixed(1) : "";
  if (eta) eta.textContent = status.status === "running" ? formatSeconds(status.eta_seconds) : "";
  if (statusLabel) {
    statusLabel.textContent = status.status;
    statusLabel.className = `status-badge ${status.status}`;
  }
  if (detailLink) {
    detailLink.href = status.detail_url;
    detailLink.hidden = status.status !== "complete";
  }
}

function setRunFormDisabled(form, disabled) {
  form.querySelectorAll("input, select, button").forEach((element) => {
    element.disabled = disabled;
  });
}

document.querySelectorAll("[data-run-id]").forEach((panel) => {
  updateRunProgress(panel);
});

async function updateCodexJob(panel) {
  const jobId = panel.dataset.codexJobId;
  const response = await fetch(`/codex-jobs/${jobId}/status`);
  if (!response.ok) return;
  const status = await response.json();
  const statusLabel = document.querySelector('[data-field="codex-status"]');
  if (statusLabel) {
    statusLabel.textContent = status.status;
    statusLabel.className = `status-badge ${status.status}`;
  }
  setText('[data-field="started"]', status.started_at || "");
  setText('[data-field="completed"]', status.completed_at || "");
  setText('[data-field="log"]', status.log_text || "");
  setText('[data-field="test-output"]', status.test_output || "");
  setText('[data-field="git-status"]', status.git_status_output || "");
  setText('[data-field="changed-files"]', (status.changed_files || []).join("\n"));
  const error = document.querySelector('[data-field="error"]');
  if (error) {
    error.hidden = !status.error_message;
    error.textContent = status.error_message || "";
  }
  if (status.status === "queued" || status.status === "running") {
    window.setTimeout(() => updateCodexJob(panel), 1000);
  }
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

document.querySelectorAll("[data-codex-job-id]").forEach((panel) => {
  updateCodexJob(panel);
});

document.querySelectorAll("[data-run-form]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (form.dataset.submitting === "true") return;
    form.dataset.submitting = "true";
    const formData = new FormData(form);
    setRunFormDisabled(form, true);

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      const panel = renderCurrentRunPanel(payload.run_id, form);
      window.history.replaceState(null, "", payload.game_url);
      updateRunProgress(panel);
    } catch (error) {
      setRunFormDisabled(form, false);
      showRunError(error.message || "Could not start the run.");
    } finally {
      form.dataset.submitting = "false";
    }
  });
});

function renderCurrentRunPanel(runId, form) {
  const container = document.getElementById("current-run-container");
  const variant = form.querySelector('[name="variant_name"]').value;
  const games = form.querySelector('[name="number_of_games"]').value;
  const bots = ["player0_bot", "player1_bot", "player2_bot"]
    .map((name) => form.querySelector(`[name="${name}"]`).selectedOptions[0].textContent)
    .join(", ");
  container.innerHTML = `
    <section class="panel" id="current-run" data-run-id="${runId}">
      <div class="section-head">
        <div>
          <h2>Current Run</h2>
          <p>${escapeHtml(variant)} · ${escapeHtml(games)} games · ${escapeHtml(bots)}</p>
        </div>
        <span class="status-badge queued" data-field="status">queued</span>
      </div>
      <div class="progress"><div class="progress-bar" style="width: 0%"></div></div>
      <p class="progress-text">0 / ${escapeHtml(games)} games (0.0%)</p>
      <dl class="metrics">
        <dt>Elapsed</dt><dd data-field="elapsed">0.0s</dd>
        <dt>Games/sec</dt><dd data-field="gps"></dd>
        <dt>ETA</dt><dd data-field="eta"></dd>
      </dl>
      <a data-field="detail-link" href="/runs/${runId}" hidden>Open run detail</a>
      <a href="#run-history">Previous Runs</a>
    </section>`;
  return container.querySelector("[data-run-id]");
}

function showRunError(message) {
  const container = document.getElementById("current-run-container");
  if (!container) return;
  container.innerHTML = `<div class="error-banner">${escapeHtml(message)}</div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}
