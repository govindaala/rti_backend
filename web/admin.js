// रिपॉजिटरी पथ: rti_backend/web/admin.js
"use strict";

const statusNode = document.getElementById("dashboard-status");
const refreshButton = document.getElementById("refresh-dashboard");
const sourceForm = document.getElementById("source-form");
const sourceStatus = document.getElementById("source-status");
const submitButton = document.getElementById("submit-source");

function addCell(row, value, href) {
  const cell = document.createElement("td");
  if (href) {
    const link = document.createElement("a");
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = value || href;
    cell.append(link);
  } else {
    cell.textContent = value === null || value === undefined ? "—" : String(value);
  }
  row.append(cell);
}

function renderBreakdown(targetId, values) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  for (const [label, count] of Object.entries(values || {})) {
    const line = document.createElement("p");
    line.textContent = label + ": " + count;
    target.append(line);
  }
}

function renderRows(targetId, rows, columns, emptyText) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  if (!rows || rows.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.textContent = emptyText;
    row.append(cell);
    target.append(row);
    return;
  }
  for (const item of rows) {
    const row = document.createElement("tr");
    for (const column of columns) {
      addCell(row, item[column.key], column.link ? item[column.link] : null);
    }
    target.append(row);
  }
}

async function loadDashboard() {
  refreshButton.disabled = true;
  statusNode.textContent = "वास्तविक सर्वर और database से आँकड़े प्राप्त हो रहे हैं...";
  try {
    const response = await fetch("/api/v1/admin/dashboard", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      cache: "no-store"
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    document.getElementById("db-status").textContent = data.database;
    const sources = data.sources || {};
    const jobs = data.jobs || {};
    const documents = data.documents || {};
    document.getElementById("source-count").textContent =
      Object.values(sources).reduce((sum, value) => sum + value, 0);
    document.getElementById("job-total").textContent =
      Object.values(jobs).reduce((sum, value) => sum + value, 0);
    document.getElementById("document-total").textContent =
      Object.values(documents).reduce((sum, value) => sum + value, 0);
    renderBreakdown("source-breakdown", sources);
    renderBreakdown("job-breakdown", jobs);
    renderBreakdown("document-breakdown", documents);
    renderRows("recent-jobs", data.recent_jobs, [
      { key: "status" }, { key: "url", link: "url" },
      { key: "discovered" }, { key: "updated_at" }
    ], "अभी कोई crawl job नहीं है।");
    renderRows("recent-documents", data.recent_documents, [
      { key: "title", link: "url" }, { key: "type" },
      { key: "status" }, { key: "created_at" }
    ], "अभी कोई दस्तावेज़ सुरक्षित नहीं हुआ है।");
    statusNode.textContent = "Live database आँकड़े अपडेट हुए: " + new Date().toLocaleTimeString();
  } catch (error) {
    statusNode.textContent = "Live dashboard उपलब्ध नहीं: " + error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

sourceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  sourceStatus.textContent = "स्रोत की अनुमति और queue की जाँच हो रही है...";
  const token = document.getElementById("admin-token").value;
  const payload = {
    url: document.getElementById("source-url").value.trim(),
    label: document.getElementById("source-label").value.trim() || null
  };
  try {
    const response = await fetch("/api/v1/admin/sources", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": token,
        Accept: "application/json"
      },
      body: JSON.stringify(payload),
      credentials: "same-origin"
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "HTTP " + response.status);
    sourceStatus.textContent = result.queued
      ? "स्रोत Queue में जुड़ गया। Job ID: " + result.job_id
      : "यह स्रोत पहले से queue/running में है। Job ID: " + result.job_id;
    document.getElementById("source-url").value = "";
    document.getElementById("source-label").value = "";
    document.getElementById("admin-token").value = "";
    await loadDashboard();
  } catch (error) {
    sourceStatus.textContent = "स्रोत नहीं जुड़ा: " + error.message;
  } finally {
    submitButton.disabled = false;
  }
});

refreshButton.addEventListener("click", loadDashboard);
loadDashboard();
window.setInterval(loadDashboard, 15000);
