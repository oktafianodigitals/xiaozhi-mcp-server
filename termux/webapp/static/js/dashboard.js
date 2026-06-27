/* ═══════════════════════════════════════════════════════════════════
   xiaozhi-mcp-console — dashboard.js  v1.1
   Vanilla JS, tanpa build step.
   ═══════════════════════════════════════════════════════════════════ */

const POLL_MS = 4000;

// ── Helpers ───────────────────────────────────────────────────────────────────

function showToast(message, type = "ok") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 3400);
}

async function apiGet(path) {
  const res = await fetch(path);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `GET ${path} → ${res.status}`);
  return data;
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `POST ${path} → ${res.status}`);
  return data;
}

function timeAgo(unixSeconds) {
  if (!unixSeconds) return "—";
  const diff = Math.max(0, Date.now() / 1000 - unixSeconds);
  if (diff < 60)   return `${Math.floor(diff)}d lalu`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
  return `${Math.floor(diff / 86400)}h lalu`;
}

function formatDatetime(unixSeconds) {
  if (!unixSeconds) return "—";
  return new Date(unixSeconds * 1000).toLocaleString("id-ID", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

// ── Connection state → UI helpers ─────────────────────────────────────────────

const STATUS_LABEL = {
  connected:    "Terhubung",
  connecting:   "Menghubungkan…",
  disconnected: "Tidak terhubung",
  error:        "Error",
};

const STATUS_PILL_CLASS = {
  connected:    "ok",
  connecting:   "connecting",
  disconnected: "",
  error:        "err",
};

function applyPillStatus(pillEl, dotEl, textEl, status) {
  if (!pillEl) return;
  pillEl.className = `pill ${STATUS_PILL_CLASS[status] || ""}`;
  if (dotEl) dotEl.style.background = "";  // CSS handles via class
  if (textEl) textEl.textContent = STATUS_LABEL[status] || status;
}

// ── Signal strip (semua halaman) ──────────────────────────────────────────────

async function refreshSignalStrip() {
  try {
    const s = await apiGet("/api/status");
    const xz = s.xiaozhi || {};
    const connected = xz.status === "connected";
    const hasError  = xz.status === "error";
    const connecting = xz.status === "connecting";

    // Node kiri: XiaoZhi Cloud
    const nodeCloud = document.getElementById("node-cloud");
    if (nodeCloud) {
      nodeCloud.classList.toggle("live", connected);
      const dot = nodeCloud.querySelector(".signal-node-dot");
      if (dot) {
        dot.style.background = connected ? "" :
          hasError ? "var(--red)" :
          connecting ? "var(--amber)" : "";
      }
    }
    setText("node-cloud-status", STATUS_LABEL[xz.status] || "—");
    setText("node-cloud-sub", xz.last_method || "");

    // Node tengah: Console
    setText("node-console-value", "online");
    setText("node-console-sub", `port ${s.network?.dashboard_port || ""}`);

    // Node kanan: Tools
    const nodeTools = document.getElementById("node-tools");
    if (nodeTools) nodeTools.classList.toggle("live", s.tools_enabled_count > 0);
    setText("node-tools-value", `${s.tools_enabled_count || 0} tool`);
    setText("node-tools-sub", `${s.tool_call_count || 0} calls`);

    // Wave animations
    const waveLeft  = document.getElementById("wave-left");
    const waveRight = document.getElementById("wave-right");
    if (waveLeft)  waveLeft.classList.toggle("live", connected);
    if (waveRight) waveRight.classList.toggle("live", connected && s.tools_enabled_count > 0);

    // Sidebar badge
    const sidebarDot   = document.getElementById("sidebar-conn-dot");
    const sidebarLabel = document.getElementById("sidebar-conn-label");
    if (sidebarDot)   sidebarDot.style.background = connected ? "var(--signal)" : hasError ? "var(--red)" : "var(--text-faint)";
    if (sidebarLabel) sidebarLabel.textContent = `XiaoZhi: ${STATUS_LABEL[xz.status] || "—"}`;

    // Settings page inline status
    const settingsPill = document.getElementById("settings-conn-pill");
    const settingsDot  = settingsPill?.querySelector(".pill-dot");
    const settingsText = document.getElementById("settings-conn-text");
    applyPillStatus(settingsPill, settingsDot, settingsText, xz.status);
    setText("settings-conn-url", xz.wss_url || "");

  } catch (_) { /* dashboard tetap tampil walau poll gagal sesaat */ }
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

setInterval(refreshSignalStrip, POLL_MS);
document.addEventListener("DOMContentLoaded", refreshSignalStrip);

// ── Halaman Status ────────────────────────────────────────────────────────────

async function refreshStatusPage() {
  if (!document.getElementById("status-page")) return;
  try {
    const s = await apiGet("/api/status");
    const xz = s.xiaozhi || {};

    // Stats
    setText("stat-uptime",  s.uptime_human);
    setText("stat-calls",   s.tool_call_count);
    setText("stat-tools",   s.tools_enabled_count);
    const errEl = document.getElementById("stat-errors");
    if (errEl) {
      errEl.textContent = s.tool_error_count;
      errEl.className   = `stat-value ${s.tool_error_count > 0 ? "err" : "ok"}`;
    }

    // Restart banner
    const banner = document.getElementById("restart-banner");
    if (banner) banner.style.display = s.restart_required ? "flex" : "none";

    // XiaoZhi connection card
    const pill    = document.getElementById("conn-status-pill");
    const pillDot = pill?.querySelector(".pill-dot");
    const pillTxt = document.getElementById("conn-status-text");
    applyPillStatus(pill, pillDot, pillTxt, xz.status);

    setText("conn-url",          xz.wss_url || "—");
    setText("conn-since",        xz.status === "connected" ? formatDatetime(xz.connected_at) : "—");
    setText("conn-last-method",  xz.last_method || "—");
    setText("conn-messages",     xz.messages_received ?? "—");

    // Error row
    const errRow = document.getElementById("conn-error-row");
    if (errRow) {
      errRow.style.display = xz.last_error ? "block" : "none";
      setText("conn-error", xz.last_error || "");
    }

    // Reconnect countdown row
    const rcRow = document.getElementById("conn-reconnect-row");
    if (rcRow) {
      const showRc = xz.status !== "connected" && xz.reconnect_count > 0;
      rcRow.style.display = showRc ? "block" : "none";
      if (showRc) {
        const next = xz.next_reconnect_in > 0 ? `reconnect dalam ${xz.next_reconnect_in}s` : "sedang reconnect…";
        setText("conn-reconnect-info", `ke-${xz.reconnect_count} · ${next}`);
      }
    }

    // Recent tool calls
    renderCallHistory(s.recent_calls || []);

  } catch (err) {
    console.warn("refreshStatusPage error:", err);
  }
}

function renderCallHistory(calls) {
  const body = document.getElementById("calls-body");
  if (!body) return;
  if (calls.length === 0) {
    body.innerHTML = '<div class="empty-state">Belum ada tool yang dipanggil.</div>';
    return;
  }
  body.innerHTML = "";
  for (const call of [...calls].reverse()) {
    const row = document.createElement("div");
    row.className = "tool-row";
    const desc = call.ok
      ? (call.result_preview || "sukses")
      : (call.error || "error");
    row.innerHTML = `
      <div class="tool-meta">
        <div class="tool-name">${call.tool}</div>
        <div class="tool-desc">${desc.substring(0, 120)} · ${call.duration_ms}ms · ${timeAgo(call.time)}</div>
      </div>
      <span class="pill ${call.ok ? "ok" : "err"}">
        <span class="pill-dot"></span>${call.ok ? "ok" : "error"}
      </span>`;
    body.appendChild(row);
  }
}

if (document.getElementById("status-page")) {
  refreshStatusPage();
  setInterval(refreshStatusPage, POLL_MS);
}

// ── Halaman Tools ─────────────────────────────────────────────────────────────

async function loadToolsPage() {
  const root = document.getElementById("tools-page");
  if (!root) return;
  let tools;
  try { tools = await apiGet("/api/tools"); }
  catch (err) { root.innerHTML = `<div class="empty-state">Gagal memuat: ${err.message}</div>`; return; }

  const LABELS = { info_search: "Info & Search", media: "Media", telegram: "Telegram", general: "Lainnya" };
  const grouped = {};
  for (const t of tools) (grouped[t.category] = grouped[t.category] || []).push(t);

  root.innerHTML = "";
  for (const [cat, items] of Object.entries(grouped)) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<div class="card-title">${LABELS[cat] || cat}</div>`;
    for (const t of items) {
      const row = document.createElement("div");
      row.className = "tool-row";
      row.innerHTML = `
        <div class="tool-meta">
          <div class="tool-name">${t.name}</div>
          <div class="tool-desc">${t.description}</div>
        </div>
        <div class="tool-actions">
          <button class="btn btn-sm" data-test="${t.name}">Test</button>
          <label class="switch">
            <input type="checkbox" data-toggle="${t.name}" ${t.enabled ? "checked" : ""}>
            <span class="switch-track"></span>
          </label>
        </div>`;
      card.appendChild(row);
    }
    root.appendChild(card);
  }

  root.querySelectorAll("[data-toggle]").forEach((input) => {
    input.addEventListener("change", async (e) => {
      const name = e.target.getAttribute("data-toggle");
      try {
        await apiPost("/api/tools/toggle", { name, enabled: e.target.checked });
        showToast(`${name} ${e.target.checked ? "diaktifkan" : "dinonaktifkan"}`, "ok");
        refreshSignalStrip();
      } catch (err) {
        showToast(`Gagal: ${err.message}`, "err");
        e.target.checked = !e.target.checked;
      }
    });
  });

  root.querySelectorAll("[data-test]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const name = e.target.getAttribute("data-test");
      const argsStr = window.prompt(`Argumen JSON untuk "${name}" (kosong = {})`, "{}");
      if (argsStr === null) return;
      let args;
      try { args = JSON.parse(argsStr || "{}"); }
      catch { showToast("JSON tidak valid", "err"); return; }
      try {
        const r = await apiPost("/api/tools/test", { name, arguments: args });
        showToast(`${name} sukses — detail di console browser`, "ok");
        console.log(`Hasil ${name}:`, r.result);
      } catch (err) { showToast(`${name} gagal: ${err.message}`, "err"); }
    });
  });
}

if (document.getElementById("tools-page")) loadToolsPage();

// ── Halaman Logs ──────────────────────────────────────────────────────────────

async function loadLogs() {
  const body = document.getElementById("logs-body");
  if (!body) return;
  const level = document.getElementById("log-level-filter")?.value || "";
  try {
    const logs = await apiGet(`/api/logs${level ? `?level=${level}` : ""}`);
    if (logs.length === 0) {
      body.innerHTML = '<div class="empty-state">Belum ada log.</div>';
      return;
    }
    body.innerHTML = "";
    for (const log of [...logs].reverse()) {
      const line = document.createElement("div");
      line.className = "log-line";
      line.innerHTML = `
        <span>${log.time}</span>
        <span class="lvl-${log.level}">${log.level}</span>
        <span class="log-msg">[${log.logger}] ${log.message}</span>`;
      body.appendChild(line);
    }
  } catch (err) { body.innerHTML = `<div class="empty-state">Gagal: ${err.message}</div>`; }
}

if (document.getElementById("logs-body")) {
  loadLogs();
  setInterval(loadLogs, POLL_MS);
  document.getElementById("log-level-filter")?.addEventListener("change", loadLogs);
}

// ── Halaman Settings ──────────────────────────────────────────────────────────

function collectFormConfig(form) {
  const data = {};
  form.querySelectorAll("[data-path]").forEach((el) => {
    // Field password kosong = tidak diubah (nilai mask dikirim balik bisa menimpa secret)
    if (el.type === "password" && el.value === "") return;
    const path = el.getAttribute("data-path").split(".");
    let node = data;
    for (let i = 0; i < path.length - 1; i++) node = node[path[i]] = node[path[i]] || {};
    let val;
    if (el.type === "checkbox")  val = el.checked;
    else if (el.type === "number") val = el.value === "" ? null : Number(el.value);
    else val = el.value;
    node[path[path.length - 1]] = val;
  });
  return data;
}

function setupSettingsForm(formId, successMsg) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = collectFormConfig(form);
    try {
      const r = await apiPost("/api/config", payload);
      showToast(successMsg, "ok");
      if (r.restart_required) {
        const b = document.getElementById("settings-restart-banner");
        if (b) b.style.display = "flex";
      }
    } catch (err) { showToast(`Gagal menyimpan: ${err.message}`, "err"); }
  });
}

setupSettingsForm("form-xiaozhi",   "Setting XiaoZhi tersimpan — reconnect otomatis");
setupSettingsForm("form-network",   "Setting jaringan tersimpan — restart untuk menerapkan");
setupSettingsForm("form-api-keys",  "API keys tersimpan");
setupSettingsForm("form-browser",   "Path Brave tersimpan");
setupSettingsForm("form-telegram",  "Setting Telegram tersimpan");

document.getElementById("btn-test-browser")?.addEventListener("click", async () => {
  const resultEl = document.getElementById("browser-test-result");
  if (resultEl) resultEl.textContent = "Mendeteksi…";
  try {
    const r = await apiGet("/api/browser/detect");
    const noteText = r.note ? ` (${r.note})` : "";
    if (resultEl) resultEl.textContent = `✅ [${r.platform}] ${r.path}${noteText}`;
    showToast("Browser terdeteksi", "ok");
  } catch (err) {
    if (resultEl) resultEl.textContent = `❌ ${err.message}`;
    showToast(`Deteksi gagal: ${err.message}`, "err");
  }
});

document.getElementById("btn-restart")?.addEventListener("click", async () => {
  if (!confirm("Restart listener jaringan sekarang? Koneksi XiaoZhi tidak terganggu.")) return;
  try { await apiPost("/api/restart", {}); showToast("Restart diminta", "ok"); }
  catch (err) { showToast(`Gagal: ${err.message}`, "err"); }
});
