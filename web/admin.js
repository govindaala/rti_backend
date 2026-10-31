// रिपॉजिटरी पथ: rti_backend/web/admin.js
"use strict";

const statusNode = document.getElementById("dashboard-status");
const refreshButton = document.getElementById("refresh-dashboard");

function renderBreakdown(targetId, values) {
  const target = document.getElementById(targetId);
  target.replaceChildren();
  for (const [label, count] of Object.entries(values || {})) {
    const line = document.createElement("p");
    line.textContent = label + ": " + count;
    target.append(line);
  }
}

async function loadDashboard() {
  refreshButton.disabled = true;
  statusNode.textContent = "सर्वर से आँकड़े प्राप्त किए जा रहे हैं...";
  try {
    const response = await fetch("/api/v1/admin/dashboard", {
      headers: { Accept: "application/json" },
      credentials: "same-origin"
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
    statusNode.textContent = "आँकड़े अपडेट हो गए।";
  } catch (error) {
    statusNode.textContent = "Dashboard डेटा उपलब्ध नहीं: " + error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadDashboard);
loadDashboard();
