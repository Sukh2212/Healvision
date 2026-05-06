// ========================= 
// HealVision Frontend JS 
// =========================

// Dynamic voice assistant placeholders (safe fallback if import fails)
let speak = () => {};
let stopSpeaking = () => {};
let getDiseaseSpeech = (d) => "";
let getChatbotSpeech = (t) => t || "";

// Try dynamic import of voiceAssistant.js
(async () => {
  try {
    const mod = await import("./voiceAssistant.js");
    if (mod?.speak) speak = mod.speak;
    if (mod?.stopSpeaking) stopSpeaking = mod.stopSpeaking;
    if (mod?.getDiseaseSpeech) getDiseaseSpeech = mod.getDiseaseSpeech;
    if (mod?.getChatbotSpeech) getChatbotSpeech = mod.getChatbotSpeech;
    console.log("✅ voiceAssistant dynamically loaded.");
  } catch (err) {
    console.warn("⚠️ voiceAssistant dynamic import failed — continuing without TTS.", err);
  }
})();

document.addEventListener("DOMContentLoaded", () => {

  // =========================
  // ✅ Google OAuth Redirect Handler
  // =========================
  const params = new URLSearchParams(window.location.search);
  const tokenFromURL = params.get("token");
  if (tokenFromURL) {
    localStorage.setItem("token", tokenFromURL);
    const cleanUrl = window.location.origin + window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);
    setTimeout(() => (window.location.href = "index.html"), 200);
    return;
  }

  // =========================
  // Constants & Elements
  // =========================
  const API_BASE = "http://127.0.0.1:5000/api";
  const CHATBOT_BASE = "http://127.0.0.1:5000/chatbot";

  const patientName = document.getElementById("patientName");
  const patientAge = document.getElementById("patientAge");
  const patientGender = document.getElementById("patientGender");
  const medicalHistory = document.getElementById("medicalHistory");
  const symptomCheckboxes = document.getElementById("symptomCheckboxes");
  const toggleSymptomGrid = document.getElementById("toggleSymptomGrid");
  const predictForm = document.getElementById("predictForm");
  const manualSymptomsInput = document.getElementById("manualSymptoms");

  const loadingBox = document.getElementById("loadingBox");
  const resultBox = document.getElementById("resultBox");
  const diseaseNameSpan = document.getElementById("diseaseName");
  const descriptionSpan = document.getElementById("diseaseDescription");
  const medicationsListSpan = document.getElementById("medicationsList");
  const precautionsListSpan = document.getElementById("precautionsList");
  const dietListSpan = document.getElementById("dietList");
  const workoutsListSpan = document.getElementById("workoutsList");

  // Chart elements
  const toggleChartBtn = document.getElementById("toggleSymptomGrid");

  const chartContainer = document.getElementById("chartContainer");
  const symptomChartCanvas = document.getElementById("symptomChart");
  let symptomChart = null;


  const viewHistoryBtn = document.getElementById("viewHistoryBtn");
  const historyPopup = document.getElementById("historyPopup");
  const historyList = document.getElementById("historyList");
  const currentPredictionPopup = document.getElementById("currentPredictionPopup");

  const aiButton = document.getElementById("aiButton");
  const dietButton = document.getElementById("dietButton");
  const emergencyButton = document.getElementById("emergencyButton");
  const tipsButton = document.getElementById("tipsButton");
  const chatPopup = document.getElementById("chatPopup");

  // =============================
// 🎤 Voice Recognition (Mic Button)
// =============================
const micButton = document.getElementById("micButton");

let micActive = false;

document.addEventListener("voice-recognized", (e) => {
  console.log("🎧 Final Text:", e.detail);

  // AUTO-FILL recognized text into chatbot input box
  const input = document.getElementById("chatInput");
  if (input) input.value = e.detail;
});

micButton?.addEventListener("click", () => {
  if (!micActive) {
    console.log("🎤 Starting mic...");
    micActive = true;
    micButton.style.background = "#28a745"; // green glow
    startListening();
  } else {
    console.log("🛑 Stopping mic...");
    micActive = false;
    micButton.style.background = ""; // reset
    stopListening();
  }
});


 
    // =========================
  // Helpers
  // =========================
  const forceHidePopup = (el) => {
    try {
      if (!el) return;
      el.style.display = "none";
      el.classList.add("d-none");
    } catch (e) {}
  };

  const showLoading = (show) => loadingBox?.classList.toggle("d-none", !show);
  const showElement = (el) => el?.classList.remove("d-none");
  const hideElement = (el) => el?.classList.add("d-none");

    // ✅ Ask AI long-message formatter
  function formatAskAIMessage(message) {
    if (!message) return "";

    // Remove leaked CSS junk
    message = message
      .replace(/scrollbar-width[^;]*;?/gi, "")
      .replace(/scrollbar-color[^;]*;?/gi, "")
      .trim();

    // Structure long content
    const lines = message
      .split(/\n|\.\s+/)
      .map(l => l.trim())
      .filter(l => l.length > 0);

    // Short text → normal paragraph
    if (lines.length < 4) {
      return `<p style="line-height:1.7;">${message}</p>`;
    }

    // Long text → bullet points
    let html = `<div class="askai-content">`;
    html += `<h4 style="margin-bottom:10px;">🧠 AI Explanation</h4><ul>`;

    lines.forEach(line => {
      html += `<li>${line.endsWith(".") ? line : line + "."}</li>`;
    });

    html += `</ul></div>`;
    return html;
  }


  // ✅ ADD THIS FUNCTION HERE 👇
  function formatDietLifestyleMessage(message) {
    if (!message) return "";

    // Remove accidental CSS text
    message = message
      .replace(/scrollbar-width[^;]*;?/gi, "")
      .replace(/scrollbar-color[^;]*;?/gi, "")
      .trim();

    // Try parsing JSON
    try {
      const data = JSON.parse(message);

      let html = "";

      if (data.diet && Array.isArray(data.diet)) {
        html += `<h4>🍎 Diet Recommendations</h4><ul>`;
        data.diet.forEach(item => {
          html += `<li>${item}</li>`;
        });
        html += `</ul>`;
      }

      if (data.workout && Array.isArray(data.workout)) {
        html += `<h4>🏃 Lifestyle & Workout</h4><ul>`;
        data.workout.forEach(item => {
          html += `<li>${item}</li>`;
        });
        html += `</ul>`;
      }

      return html || "<p>No recommendations available.</p>";
    } catch (e) {
      return `<p>${message}</p>`;
    }
  }

  // ================================
// 🧾 PDF REPORT HELPERS
// ================================

function buildPdfReport(patient, pred, selectedSymptoms) {
  return `
    <div style="font-family:Arial; padding:30px; color:#000;">
      <h2 style="text-align:center;">HealVision Prediction Report</h2>
      <hr/>

      <p><b>Name:</b> ${patient.name}</p>
      <p><b>Age:</b> ${patient.age}</p>
      <p><b>Gender:</b> ${patient.gender}</p>
      <p><b>Medical History:</b> ${patient.history || "—"}</p>

      <hr/>

      <h3>Symptoms</h3>
      <p>${selectedSymptoms}</p>

      <h3>Disease</h3>
      <p>${pred.disease || "—"}</p>

      <h3>Description</h3>
      <p>${pred.description || "—"}</p>

      <h3>Medicines</h3>
      <p>${(pred.medicines || []).join(", ") || "—"}</p>

      <h3>Precautions</h3>
      <p>${(pred.precautions || []).join(", ") || "—"}</p>

      <h3>Diet</h3>
      <p>${(pred.diet || []).join(", ") || "—"}</p>

      <h3>Workout</h3>
      <p>${(pred.workout || []).join(", ") || "—"}</p>

      <br/>
      <small>Generated by HealVision AI</small>
    </div>
  `;
}




  forceHidePopup(historyPopup);
  forceHidePopup(currentPredictionPopup);

  // =========================
  // Load Symptoms
  // =========================
 const createCheckboxLabel = (symptom) => {
  const wrapper = document.createElement("div");
  wrapper.className = "symptom-item"; // use grid item class
  wrapper.innerHTML = `
    <label>
      <input class="symptomCheckbox" type="checkbox" value="${symptom}">
      ${symptom}
    </label>`;
  return wrapper;
};

// when checkbox toggled, sync checked values to manual input
const syncSelectedSymptoms = () => {
  const selected = Array.from(document.querySelectorAll(".symptomCheckbox:checked"))
    .map(cb => cb.value);
  manualSymptomsInput.value = selected.join(", ");
};

const getSelectedSymptoms = () => {
  const result = {};
  document.querySelectorAll(".symptomCheckbox:checked").forEach((n) => (result[n.value] = 1));
  return result;
};

const parseManualSymptoms = (text) =>
  text?.split(",").map((s) => s.trim()).filter(Boolean) || [];

const loadSymptomsIfEmpty = async () => {
  let container = document.querySelector("#symptomCheckboxes .symptom-grid");
  if (!container) {
    container = document.createElement("div");
    container.className = "symptom-grid";
    symptomCheckboxes.appendChild(container);
  }
  if (container.childElementCount > 0) return;
  showLoading(true);
  try {
    const res = await fetch(`${API_BASE}/symptoms`);
    const data = await res.json();
    console.log("✅ Symptoms fetched:", data);

    const list = data.symptoms || [];
    container.innerHTML = "";
    list.forEach((s) => {
      const item = createCheckboxLabel(s);
      container.appendChild(item);
    });

    // ✅ Add listener for syncing manual input
    container.querySelectorAll(".symptomCheckbox").forEach(cb =>
      cb.addEventListener("change", syncSelectedSymptoms)
    );

  } catch (err) {
    console.error("❌ Could not load symptoms list.", err);
    alert("❌ Could not load symptoms list.");
  } finally {
    showLoading(false);
  }
};
  toggleSymptomGrid?.addEventListener("click", async () => {
    const hidden = symptomCheckboxes.classList.contains("d-none");
    if (hidden) {
      symptomCheckboxes.classList.remove("d-none");
      toggleSymptomGrid.textContent = "Hide Symptoms";
      await loadSymptomsIfEmpty();
    } else {
      symptomCheckboxes.classList.add("d-none");
      toggleSymptomGrid.textContent = "Show Symptoms";
    }
  });

  // =========================
  // Prediction Form Submit
  // =========================
  predictForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    stopSpeaking?.();
    forceHidePopup(historyPopup);

    const patient = {
      name: patientName?.value?.trim() || "Unknown",
      age: patientAge?.value?.trim() || "N/A",
      gender: patientGender?.value?.trim() || "N/A",
      history: medicalHistory?.value?.trim() || "",
    };

    const selected = getSelectedSymptoms();
    parseManualSymptoms(manualSymptomsInput?.value).forEach((m) => (selected[m] = 1));
    if (Object.keys(selected).length < 2) return alert("⚠️ Please provide at least 2 symptoms.");

    showLoading(true);
    try {
      const payload = { patient, symptoms: selected };
      const res = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      showLoading(false);
      if (!res.ok && data.error) return alert(data.error);

      const pred = data.predictions?.[0];
      if (!pred) return alert("No prediction found.");

      diseaseNameSpan.textContent = pred.disease || "Unknown";
      descriptionSpan.textContent = pred.description || "—";
      medicationsListSpan.textContent = (pred.medicines || []).join(", ") || "—";
      precautionsListSpan.textContent = (pred.precautions || []).join(", ") || "—";
      dietListSpan.textContent = (pred.diet || []).join(", ") || "—";
      workoutsListSpan.textContent = (pred.workout || []).join(", ") || "—";
      const confidenceSpan = document.getElementById("confidenceField");
      if(confidenceSpan) confidenceSpan.textContent = (pred.confidence * 100).toFixed(2) + "%";


      showElement(resultBox);
      showElement(viewHistoryBtn);

      const reportPopup = document.getElementById("reportPopup");
const reportContent = document.getElementById("reportContent");

const selectedSymptomsList = Object.keys(selected).join(", ");

reportContent.innerHTML = `
  <p><strong>Name:</strong> ${patient.name}</p>
  <p><strong>Age:</strong> ${patient.age}</p>
  <p><strong>Gender:</strong> ${patient.gender}</p>
  <p><strong>Medical History:</strong> ${patient.history || "—"}</p>
  <hr>
  <p><strong>Symptoms:</strong> ${selectedSymptomsList}</p>
  <p><strong>Disease:</strong> ${pred.disease || "—"}</p>
  <p><strong>Description:</strong> ${pred.description || "—"}</p>
  <p><strong>Medicines:</strong> ${(pred.medicines || []).join(", ") || "—"}</p>
  <p><strong>Precautions:</strong> ${(pred.precautions || []).join(", ") || "—"}</p>
  <p><strong>Diet:</strong> ${(pred.diet || []).join(", ") || "—"}</p>
  <p><strong>Workout:</strong> ${(pred.workout || []).join(", ") || "—"}</p>
`;

reportPopup.style.display = "flex";

document.getElementById("closeReportBtn")?.addEventListener("click", () => {
  reportPopup.style.display = "none";
});

document.getElementById("downloadPdfBtn")?.addEventListener("click", () => {

  const container = document.createElement("div");

  container.innerHTML = buildPdfReport(
    patient,
    pred,
    selectedSymptomsList
  );

  // ✅ Must be visible for html2canvas
  container.style.position = "absolute";
  container.style.left = "0";
  container.style.top = "0";
  container.style.width = "210mm";
  container.style.background = "#ffffff";
  container.style.color = "#000";
  container.style.padding = "20px";
  container.style.zIndex = "-1";

  document.body.appendChild(container);

  // 🔥 CRITICAL FIX: wait for DOM paint
  setTimeout(() => {
    html2pdf()
      .set({
        filename: "HealVision_Prediction_Report.pdf",
        margin: 10,
        html2canvas: {
          scale: 2,
          useCORS: true,
          logging: false
        },
        jsPDF: {
          unit: "mm",
          format: "a4",
          orientation: "portrait"
        }
      })
      .from(container)
      .save()
      .then(() => {
        document.body.removeChild(container);
      });
  }, 300); // 👈 THIS IS THE MAGIC
});






      try {
  // Combine patient info + prediction for full speech
  const fullReport = {
    ...pred,
    name: patient.name,
    age: patient.age,
    gender: patient.gender
  };
  const speechText = getDiseaseSpeech(fullReport);
  if (speechText) speak(speechText, "disease");
} catch (err) {
  console.error("Speech generation error:", err);
}

    } catch {
      showLoading(false);
      alert("❌ Prediction failed.");
    }
  });

  // =========================
  // History
  // =========================
  viewHistoryBtn?.addEventListener("click", async (e) => {
    e.preventDefault();
    showLoading(true);
    try {
      const res = await fetch(`${API_BASE}/history`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });
      const data = await res.json();
      showLoading(false);
      const list = data.history || [];
      historyList.innerHTML = list.length
        ? list.map((rec) => `
          <div class="mb-2 p-2 border rounded">
            <strong>${rec.name}</strong> — ${rec.disease}
            <div><small>Age: ${rec.age}, Gender: ${rec.gender}</small></div>
            <div><small>Medicines: ${(rec.medicines || []).join(", ")}</small></div>
          </div>`).join("")
        : "<p class='text-muted text-center'>No history found.</p>";
      historyPopup.style.display = "flex";
      historyPopup.classList.remove("d-none");
    } catch (err) {
      showLoading(false);
      console.error("History fetch failed:", err);
    }
  });
  window.closePopup = () => {
    forceHidePopup(historyPopup);
    stopSpeaking?.();
  };


  // =============================
// 🆘 Emergency Visual Alert + Voice
// =============================
function showEmergencyAlert(message = "⚠️ This may be a medical emergency. Please seek help immediately.") {
  // Avoid duplicates
  if (document.getElementById("emergency-overlay")) return;

  // Stop other voice output and start emergency alert
  stopSpeaking?.();
  speak(message);

  // Overlay UI
  const overlay = document.createElement("div");
  overlay.id = "emergency-overlay";
  overlay.style.position = "fixed";
  overlay.style.top = "0";
  overlay.style.left = "0";
  overlay.style.width = "100vw";
  overlay.style.height = "100vh";
  overlay.style.background = "rgba(255,0,0,0.85)";
  overlay.style.display = "flex";
  overlay.style.flexDirection = "column";
  overlay.style.justifyContent = "center";
  overlay.style.alignItems = "center";
  overlay.style.color = "white";
  overlay.style.textAlign = "center";
  overlay.style.padding = "20px";
  overlay.style.zIndex = "9999";
  overlay.style.animation = "pulse 1s infinite alternate";

  overlay.innerHTML = `
    <div style="font-size:2rem; font-weight:bold;">🚨 EMERGENCY ALERT 🚨</div>
    <p style="margin-top:15px; font-size:1.8rem; font-weight:bold; color:#fff; text-shadow:0 0 8px rgba(255,255,255,0.9);">${message}</p>
    <div style="margin-top:25px;">
      <button id="findHospital" style="background:white; color:red; font-weight:bold; border:none; padding:10px 20px; border-radius:10px; cursor:pointer;">🏥 Find Nearest Hospital</button>
      <button id="closeEmergency" style="background:red; color:white; border:none; padding:10px 20px; border-radius:10px; margin-left:10px; cursor:pointer;">Close</button>
    </div>
  `;
  document.body.appendChild(overlay);

  document.getElementById("closeEmergency")?.addEventListener("click", () => {
    document.body.removeChild(overlay);
    stopSpeaking?.();
  });

  document.getElementById("findHospital")?.addEventListener("click", () => {
    const query = "hospitals near me";
    window.open(`https://www.google.com/maps/search/${encodeURIComponent(query)}`, "_blank");
  });
}

// Add pulse animation dynamically
const pulseStyle = document.createElement("style");
pulseStyle.innerHTML = `
@keyframes pulse {
  from { background-color: rgba(255,0,0,0.85); }
  to { background-color: rgba(255,80,80,0.9); }
}`;
document.head.appendChild(pulseStyle);


// =============================
// 🌐 Ask AI Overlay
// =============================
function showAskAIOverlay(message = "💬 Welcome to Ask AI Mode!") {
  if (document.getElementById("askai-overlay")) return;
  stopSpeaking?.();
  speak(message);

  const overlay = document.createElement("div");
  overlay.id = "askai-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100vw",
    height: "100vh",
    background: "rgba(0,123,255,0.90)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    color: "white",
    textAlign: "center",
    padding: "20px",
    zIndex: "9999",
  });

  overlay.innerHTML = `
  <div style="
    font-size:2rem;
    font-weight:bold;
    margin-bottom:12px;
  ">
    🤖 ASK AI MODE
  </div>

  <div style="
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(6px);
    border-radius: 14px;
    padding: 18px;
    max-width: 900px;
    width: 90%;
    max-height: 65vh;
    overflow-y: auto;
    color: #ffffff;
    font-size: 1.25rem;
    line-height: 1.8;
  ">
    ${formatAskAIMessage(message)}
  </div>

  <div style="margin-top:25px;">
    <button id="closeAskAI"
      style="
        background:white;
        color:#007bff;
        border:none;
        padding:10px 24px;
        border-radius:12px;
        cursor:pointer;
        font-weight:600;
      ">
      Close
    </button>
  </div>
`;


  document.body.appendChild(overlay);

  document.getElementById("closeAskAI").addEventListener("click", () => {
    document.body.removeChild(overlay);
    stopSpeaking?.();
  });
}

// =============================
// 🥦 Diet & Lifestyle Overlay
// =============================
function showDietOverlay(message = "🍎 Stay Healthy! Explore diet & lifestyle tips!") {
  if (document.getElementById("diet-overlay")) return;
  stopSpeaking?.();
  speak(message);

  const overlay = document.createElement("div");
  overlay.id = "diet-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100vw",
    height: "100vh",
    background: "rgba(40,167,69,0.90)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    color: "white",
    textAlign: "center",
    padding: "20px",
    zIndex: "9999",
    animation: "pulseDiet 1.5s infinite alternate",
  });

  overlay.innerHTML = `
  <div style="font-size:2rem; font-weight:bold;">🍎 DIET & LIFESTYLE</div>

  <div style="
    margin-top:15px;
    font-size:1.4rem;
    font-weight:500;
    color:#fff;
    text-shadow:0 0 8px rgba(0,0,0,0.9);
    max-height:60vh;
    overflow-y:auto;
    padding-right:10px;
  ">
    ${formatDietLifestyleMessage(message)}
  </div>

  <div style="margin-top:25px;">
    <button id="seeTips" style="background:white;color:#28a745;border:none;padding:10px 20px;border-radius:10px;cursor:pointer;">
      🍽️ View Diet Plan
    </button>
    <button id="closeDiet" style="background:#28a745;color:white;border:none;padding:10px 20px;border-radius:10px;margin-left:10px;cursor:pointer;">
      Close
    </button>
  </div>
`;

  document.body.appendChild(overlay);

  document.getElementById("seeTips").addEventListener("click", () => {
    window.open("https://www.healthline.com/nutrition", "_blank");
  });
  document.getElementById("closeDiet").addEventListener("click", () => {
    document.body.removeChild(overlay);
    stopSpeaking?.();
  });
}

// =============================
// 💡 Daily Health Tips Overlay
// =============================
function showTipsOverlay(message = "💡 Your Daily Health Tip!") {
  if (document.getElementById("tips-overlay")) return;
  stopSpeaking?.();
  speak(message);

  const overlay = document.createElement("div");
  overlay.id = "tips-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100vw",
    height: "100vh",
    background: "rgba(255,193,7,0.90)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    color: "#212529",
    textAlign: "center",
    padding: "20px",
    zIndex: "9999",
    animation: "pulseTips 1.5s infinite alternate",
  });

  overlay.innerHTML = `
    <div style="font-size:2rem; font-weight:bold;">💡 DAILY HEALTH TIP</div>
    <p style="margin-top:15px; font-size:1.5rem;">${message}</p>
    <div style="margin-top:25px;">
      <button id="getAnotherTip" style="background:white;color:#ffc107;border:none;padding:10px 20px;border-radius:10px;cursor:pointer;">🔁 New Tip</button>
      <button id="closeTips" style="background:#ffc107;color:black;border:none;padding:10px 20px;border-radius:10px;margin-left:10px;cursor:pointer;">Close</button>
    </div>
  `;
  document.body.appendChild(overlay);

  document.getElementById("getAnotherTip").addEventListener("click", async () => {
    const tips = [
      "Drink 8 glasses of water daily 💧",
      "Sleep at least 7 hours a night 😴",
      "Take a 10-minute walk after meals 🚶‍♂️",
      "Eat more fruits and vegetables 🥦🍎",
      "Avoid screens 1 hour before bed 📵"
    ];
    const randomTip = tips[Math.floor(Math.random() * tips.length)];
    overlay.querySelector("p").textContent = randomTip;
    speak(randomTip);
  });

  document.getElementById("closeTips").addEventListener("click", () => {
    document.body.removeChild(overlay);
    stopSpeaking?.();
  });
}

// Add custom animations
const extraStyle = document.createElement("style");
extraStyle.innerHTML = `
@keyframes pulseAI {
  from { background-color: rgba(0,123,255,0.85); }
  to { background-color: rgba(0,150,255,0.9); }
}
@keyframes pulseDiet {
  from { background-color: rgba(40,167,69,0.85); }
  to { background-color: rgba(60,187,89,0.9); }
}
@keyframes pulseTips {
  from { background-color: rgba(255,193,7,0.85); }
  to { background-color: rgba(255,213,50,0.9); }
}`;
document.head.appendChild(extraStyle);

// ✅ Ask AI clean list styling
const askAIStyle = document.createElement("style");
askAIStyle.innerHTML = `
.askai-content ul {
  padding-left: 20px;
}
.askai-content li {
  margin-bottom: 10px;
}
`;
document.head.appendChild(askAIStyle);




  // =========================
  // ✅ Chatbot 
  // =========================
  const appendChatMessage = (sender, text, label = "") => {
    const msgDiv = document.createElement("div");
    msgDiv.className = sender === "user" ? "chat-bubble user-bubble" : "chat-bubble bot-bubble";
    msgDiv.innerHTML = label ? `<strong>${label}</strong><br>${text}` : text;
    const container = document.getElementById("chatMessages");
    container?.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  };

  const showChatPopup = (mode = "ai") => {
    if (!chatPopup) return;
    const titles = {
      ai: "🤖 AI Chatbot",
      diet: "🍎 Diet & Lifestyle Bot",
      emergency: "🚨 Emergency Assistant",
      tips: "💡 Health Tips Bot",
    };
    chatPopup.innerHTML = `
      <div class="popup-content border rounded p-3 bg-white shadow" style="max-width:720px;">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h5>${titles[mode]}</h5>
          <button id="closeChatPopupBtn" class="btn btn-sm btn-outline-secondary">Close</button>
        </div>
        <div id="chatMessages" class="chat-messages" style="max-height:300px;overflow:auto;margin-bottom:8px;"></div>
        <textarea id="chatInput" class="form-control mb-2" placeholder="Type your message..."></textarea>
        <div class="text-end"><button id="sendChatBtn" class="btn btn-primary btn-sm">Send</button></div>
      </div>`;
    chatPopup.style.display = "flex";

    document.getElementById("closeChatPopupBtn")?.addEventListener("click", () => {
      chatPopup.style.display = "none";
      stopSpeaking?.();
    });

    // ✅ Send & receive chatbot messages
    document.getElementById("sendChatBtn")?.addEventListener("click", async () => {
      const input = document.getElementById("chatInput");
      const msg = input.value.trim();
      if (!msg) return;

      appendChatMessage("user", msg);
      input.value = "";

      const container = document.getElementById("chatMessages");
      const typingDiv = document.createElement("div");
      typingDiv.className = "chat-bubble bot-bubble text-muted";
      typingDiv.textContent = "⏳ Bot is typing...";
      container.appendChild(typingDiv);
      container.scrollTop = container.scrollHeight;

      try {
        stopSpeaking?.();
        const res = await fetch(`${CHATBOT_BASE}/chat/${mode}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg }),
        });

        const data = await res.json();

        // remove typing indicator if present
        try { if (container.contains(typingDiv)) container.removeChild(typingDiv); } catch (e) {}

       
        // Prefer format: { mode: "...", reply: { provider: "...", text: "..." } }
        let botText = "";
        let provider = "";

        if (data && typeof data === "object") {
          // mode + reply + text format (your confirmed preferred format)
          if (data.mode && data.reply) {
            if (typeof data.reply === "string") {
              botText = data.reply;
            } else if (typeof data.reply.text === "string") {
              botText = data.reply.text;
            } else if (typeof data.reply.message === "string") {
              botText = data.reply.message;
            } else {
              // fallback: stringify reply object
              botText = JSON.stringify(data.reply);
            }
            provider = data.reply.provider || "";
          }
          // older shapes
          else if (typeof data.response === "string") {
            botText = data.response;
          } else if (typeof data.reply === "string") {
            botText = data.reply;
          } else if (typeof data.reply === "object" && (data.reply.text || data.reply.message)) {
            botText = data.reply.text || data.reply.message;
            provider = data.reply.provider || "";
          } else if (data.output && (typeof data.output === "string" || typeof data.output.text === "string")) {
            botText = typeof data.output === "string" ? data.output : data.output.text;
          } else {
            botText = "⚠️ Unexpected chatbot format.";
          }
        } else if (typeof data === "string") {
          botText = data;
        } else {
          botText = "⚠️ Unexpected chatbot format.";
        }

        // build label with provider if available
        const titles = {
          ai: "🤖 AI Chatbot",
          diet: "🍎 Diet & Lifestyle Bot",
          emergency: "🚨 Emergency Assistant",
          tips: "💡 Health Tips Bot",
        };
        const labelBase = titles[mode] || "HealVision Chatbot";
        const label = provider ? `${labelBase} — ${provider}` : labelBase;

        appendChatMessage("bot", botText, label);
        // ✅ Mode-specific overlays
        if (data.mode === "emergency") {
          showEmergencyAlert(botText || "⚠️ This may be a medical emergency. Please seek help immediately.");
        } else if (data.mode === "ai") {
          showAskAIOverlay(botText || "💬 Welcome to Ask AI Mode!");
        } else if (data.mode === "diet") {
          showDietOverlay(botText || "🍎 Stay Healthy! Explore diet & lifestyle tips!");
        } else if (data.mode === "tips") {
          showTipsOverlay(botText || "💡 Your Daily Health Tip!");
        } else if (botText) {
         speak(getChatbotSpeech(botText), "chat");
       }



      } catch (err) {
        console.error("Chatbot error:", err);
        try { if (container.contains(typingDiv)) container.removeChild(typingDiv); } catch (e) {}
        const titles = {
          ai: "🤖 AI Chatbot",
          diet: "🍎 Diet & Lifestyle Bot",
          emergency: "🚨 Emergency Assistant",
          tips: "💡 Health Tips Bot",
        };
        appendChatMessage("bot", "⚠️ Chatbot Error! Please try again later.", titles[mode]);
      }
    });
  };

  aiButton?.addEventListener("click", () => showChatPopup("ai"));
  dietButton?.addEventListener("click", () => showChatPopup("diet"));
  emergencyButton?.addEventListener("click", () => showChatPopup("emergency"));
  tipsButton?.addEventListener("click", () => showChatPopup("tips"));

  
// ===============================
// 🎤 Voice Symptoms Integration
// ===============================
document.addEventListener("voice-listen-start", () => {
  document.getElementById("listeningOverlay")?.classList.remove("d-none");
  document.getElementById("voiceWaveform")?.classList.remove("d-none");
});

document.addEventListener("voice-listen-end", () => {
  const input = document.getElementById("manualSymptoms");
  if (voiceBuffer) {
    input.value = voiceBuffer.trim().replace(/^,|,$/g, "");
  }
  voiceBuffer = ""; // reset buffer

  // hide overlay
  document.getElementById("listeningOverlay")?.classList.add("d-none");
  document.getElementById("voiceWaveform")?.classList.add("d-none");
});
// ===== Voice buffer to accumulate all recognized chunks =====
let voiceBuffer = "";

document.addEventListener("voice-recognized", (event) => {
  if (!window.isListening) return;

  const text = event.detail.trim();
  if (!text) return;
  // Accumulate in buffer, do NOT update input yet
  voiceBuffer += voiceBuffer ? ", " + text : text;
  input.value = voiceBuffer;

  // Hide mic UI
  document.getElementById("listeningOverlay")?.classList.add("d-none");
  document.getElementById("voiceWaveform")?.classList.add("d-none");
});

});

