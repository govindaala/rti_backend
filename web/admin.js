// रिपॉजिटरी पथ: rti_backend/web/admin.js
"use strict";

// Admin dashboard केवल अपने backend की health जाँच करता है; privileged API अभी नहीं हैं।
const healthButton = document.getElementById("check-health");
const healthResult = document.getElementById("health-result");
healthButton.addEventListener("click", async () => {
  healthButton.disabled = true;
  healthResult.textContent = "Backend से संपर्क किया जा रहा है...";
  try {
    const response = await fetch("/api/v1/health", {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const payload = await response.json();
    healthResult.textContent = "Backend उपलब्ध है: " + JSON.stringify(payload);
  } catch (error) {
    healthResult.textContent = "Backend health जाँच विफल: " + error.message;
  } finally {
    healthButton.disabled = false;
  }
});

// Login form disabled है; credentials browser में जमा या कहीं भेजे नहीं जाते।
