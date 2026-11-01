"use strict";

const loginPanel = document.getElementById("login-panel");
const adminContent = document.getElementById("admin-content");
const loginForm = document.getElementById("login-form");
const loginStatus = document.getElementById("login-status");
const refreshButton = document.getElementById("refresh-dashboard");
const seedButton = document.getElementById("seed-default-sources");
const catalogStatus = document.getElementById("catalog-status");
const sourceForm = document.getElementById("source-form");
const sourceStatus = document.getElementById("source-status");
const submitButton = document.getElementById("submit-source");
let csrfToken = "";
let latestDocuments = [];

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (csrfToken && options.method && options.method !== "GET") headers.set("X-CSRF-Token", csrfToken);
  return fetch(path, { ...options, headers, credentials: "same-origin", cache: "no-store" });
}

function addCell(row, value, href) {
  const cell = document.createElement("td");
  if (href) {
    const link = document.createElement("a");
    link.href = href; link.target = "_blank"; link.rel = "noopener noreferrer";
    link.textContent = value || href; cell.append(link);
  } else cell.textContent = value == null ? "—" : String(value);
  row.append(cell);
}

function renderBreakdown(id, values) {
  const target = document.getElementById(id); target.replaceChildren();
  for (const [label, count] of Object.entries(values || {})) {
    const line = document.createElement("p"); line.textContent = label + ": " + count; target.append(line);
  }
}

function renderRows(id, rows, columns, emptyText) {
  const target = document.getElementById(id); target.replaceChildren();
  if (!rows?.length) {
    const row = document.createElement("tr"); const cell = document.createElement("td");
    cell.colSpan = columns.length; cell.textContent = emptyText; row.append(cell); target.append(row); return;
  }
  for (const item of rows) {
    const row = document.createElement("tr");
    for (const column of columns) addCell(row, item[column.key], column.link ? item[column.link] : null);
    target.append(row);
  }
}

function renderDocumentRows(rows) {
  const target = document.getElementById("recent-documents"); target.replaceChildren();
  if (!rows?.length) {
    const row = document.createElement("tr"); const cell = document.createElement("td");
    cell.colSpan = 5; cell.textContent = "अभी कोई दस्तावेज़ सुरक्षित नहीं हुआ है।"; row.append(cell); target.append(row); return;
  }
  for (const item of rows) {
    const row = document.createElement("tr");
    addCell(row, item.title, item.url); addCell(row, item.type); addCell(row, item.status); addCell(row, item.created_at);
    const action = document.createElement("td");
    if (item.status === "review_required") {
      const button = document.createElement("button"); button.type = "button"; button.className = "secondary";
      button.textContent = "समीक्षा के बाद Verify";
      button.addEventListener("click", async () => {
        if (!window.confirm("क्या आपने मूल सरकारी स्रोत, निर्णय की तारीख, पूरा पाठ और बाद के/overruling निर्णय जाँच लिए हैं?")) return;
        const note = window.prompt("समीक्षा टिप्पणी लिखें (कम से कम 20 अक्षर):");
        if (!note || note.trim().length < 20) { sourceStatus.textContent = "टिप्पणी कम से कम 20 अक्षरों की होनी चाहिए।"; return; }
        button.disabled = true;
        try {
          const response = await api("/api/v1/admin/documents/" + encodeURIComponent(item.id) + "/verify", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ review_note: note.trim(), confirm_reviewed: true })
          });
          const result = await response.json(); if (!response.ok) throw new Error(result.detail || "HTTP " + response.status);
          sourceStatus.textContent = "मानव समीक्षा दर्ज: " + result.document_id; await loadDashboard();
        } catch (error) { sourceStatus.textContent = "Verify नहीं हुआ: " + error.message; button.disabled = false; }
      });
      action.append(button);
    } else action.textContent = "—";
    row.append(action); target.append(row);
  }
}

async function loadDashboard() {
  refreshButton.disabled = true;
  const status = document.getElementById("dashboard-status");
  status.textContent = "वास्तविक सर्वर और database से आँकड़े प्राप्त हो रहे हैं...";
  try {
    const response = await api("/api/v1/admin/dashboard");
    if (response.status === 401) { showLogin(); return; }
    const data = await response.json(); if (!response.ok) throw new Error(data.detail || "HTTP " + response.status);
    latestDocuments = data.recent_documents || [];
    document.getElementById("db-status").textContent = data.database;
    const sources = data.sources || {}, jobs = data.jobs || {}, docs = data.documents || {};
    document.getElementById("source-count").textContent = Object.values(sources).reduce((a, b) => a + b, 0);
    document.getElementById("job-total").textContent = Object.values(jobs).reduce((a, b) => a + b, 0);
    document.getElementById("document-total").textContent = Object.values(docs).reduce((a, b) => a + b, 0);
    const metrics = data.metrics || {};
    document.getElementById("read-document-total").textContent = metrics.read_documents ?? "—";
    document.getElementById("decision-total").textContent = metrics.decision_documents ?? "—";
    const bytes = Number(metrics.extracted_text_bytes || 0);
    document.getElementById("extracted-size").textContent = bytes >= 1073741824
      ? (bytes / 1073741824).toFixed(2) + " GB"
      : bytes >= 1048576 ? (bytes / 1048576).toFixed(2) + " MB"
      : bytes >= 1024 ? (bytes / 1024).toFixed(2) + " KB" : bytes + " bytes";
    renderBreakdown("source-breakdown", sources); renderBreakdown("job-breakdown", jobs); renderBreakdown("document-breakdown", docs);
    renderRows("recent-jobs", data.recent_jobs, [
      { key: "status" }, { key: "url", link: "url" }, { key: "discovered" }, { key: "updated_at" }
    ], "अभी कोई crawl job नहीं है।");
    renderDocumentRows(latestDocuments);
    status.textContent = "Live database आँकड़े अपडेट हुए: " + new Date().toLocaleTimeString();
  } catch (error) { status.textContent = "Live dashboard उपलब्ध नहीं: " + error.message; }
  finally { refreshButton.disabled = false; }
}

function showLogin() {
  adminContent.hidden = true; loginPanel.hidden = false; csrfToken = "";
}

async function checkSession() {
  try {
    const response = await fetch("/api/v1/admin/auth/me", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) { showLogin(); return; }
    const data = await response.json(); csrfToken = data.csrf_token;
    loginPanel.hidden = true; adminContent.hidden = false; await loadDashboard();
  } catch (_) { showLogin(); }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.getElementById("login-button"); button.disabled = true;
  loginStatus.textContent = "लॉगिन जाँचा जा रहा है...";
  try {
    const response = await fetch("/api/v1/admin/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        admin_id: document.getElementById("admin-id").value,
        admin_pass: document.getElementById("admin-pass").value
      })
    });
    const data = await response.json(); if (!response.ok) throw new Error(data.detail || "लॉगिन विफल");
    csrfToken = data.csrf_token; document.getElementById("admin-pass").value = "";
    loginPanel.hidden = true; adminContent.hidden = false; await loadDashboard();
  } catch (error) { loginStatus.textContent = error.message; }
  finally { button.disabled = false; }
});

sourceForm.addEventListener("submit", async (event) => {
  event.preventDefault(); submitButton.disabled = true; sourceStatus.textContent = "स्रोत की अनुमति और queue की जाँच हो रही है...";
  try {
    const response = await api("/api/v1/admin/sources", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: document.getElementById("source-url").value.trim(),
        label: document.getElementById("source-label").value.trim() || null
      })
    });
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || "HTTP " + response.status);
    sourceStatus.textContent = result.queued ? "स्रोत Queue में जुड़ गया। Job ID: " + result.job_id : "स्रोत पहले से queue/running में है। Job ID: " + result.job_id;
    document.getElementById("source-url").value = ""; document.getElementById("source-label").value = "";
    await loadDashboard();
  } catch (error) { sourceStatus.textContent = "स्रोत नहीं जुड़ा: " + error.message; }
  finally { submitButton.disabled = false; }
});

document.getElementById("logout-button").addEventListener("click", async () => {
  try { await api("/api/v1/admin/auth/logout", { method: "POST" }); } finally { showLogin(); }
});
refreshButton.addEventListener("click", loadDashboard);
checkSession();
window.setInterval(() => { if (!adminContent.hidden) loadDashboard(); }, 15000);


seedButton.addEventListener("click", async () => {
  if (!window.confirm("डिफॉल्ट आधिकारिक कैटलॉग के स्रोत डेटाबेस queue में डालें? इससे सार्वजनिक सरकारी वेबसाइटों की crawling शुरू हो सकती है।")) return;
  seedButton.disabled = true;
  catalogStatus.textContent = "डिफॉल्ट स्रोत queue में जोड़े जा रहे हैं...";
  try {
    const response = await api("/api/v1/admin/sources/seed-defaults", { method: "POST" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "HTTP " + response.status);
    catalogStatus.textContent = "कैटलॉग: " + result.catalogue_sources +
      " | नई jobs: " + result.queued_jobs_added +
      " | पहले से मौजूद sources: " + result.sources_already_present;
    await loadDashboard();
  } catch (error) {
    catalogStatus.textContent = "डिफॉल्ट स्रोत queue नहीं हुए: " + error.message;
  } finally { seedButton.disabled = false; }
});
