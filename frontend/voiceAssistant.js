/* ======================================================
   HealVision Voice Assistant 
   Final Enhanced Version + Prediction Report Speech
   ====================================================== */

// =====================================================
// 🔊 TEXT-TO-SPEECH (TTS) — Speak, Stop, Helpers
// =====================================================

// Check browser support
function isVoiceSupported() {
  return "speechSynthesis" in window && typeof SpeechSynthesisUtterance !== "undefined";
}

// Control flag
let isSpeaking = false;
let voiceBuffer = "";


// 🔊 Speak function
export function speak(text, type = "general") {
  try {
    if (!isVoiceSupported()) {
      console.warn("Speech synthesis NOT supported.");
      return;
    }

    // Global voice toggle
    const toggle = document.getElementById("voiceToggle");
    if (toggle && !toggle.checked) {
      console.log("Voice mode OFF — skipping speech.");
      return;
    }

    // Cancel ongoing speech
    window.speechSynthesis.cancel();
    isSpeaking = false;

    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-IN";
    utter.rate = type === "chat" ? 1.05 : 0.98;
    utter.pitch = 1;
    utter.volume = 1;

    // Events
    utter.onstart = () => { isSpeaking = true; console.log("🎤 Speaking..."); };
    utter.onend   = () => { isSpeaking = false; console.log("✅ Speech ended"); };
    utter.onerror = (e) => { isSpeaking = false; console.error("TTS Error:", e); };

    // Select Indian voice if available
    let voices = window.speechSynthesis.getVoices();
    const speakNow = () => {
      const indian = voices.find(v => v.lang.includes("en-IN") || v.name.toLowerCase().includes("india"));
      if (indian) utter.voice = indian;
      window.speechSynthesis.speak(utter);
    };

    if (!voices.length) {
      window.speechSynthesis.onvoiceschanged = () => {
        voices = window.speechSynthesis.getVoices();
        speakNow();
      };
    } else {
      speakNow();
    }

  } catch (err) {
    console.error("Speech Error:", err);
  }
}

// 🛑 Stop speaking
export function stopSpeaking() {
  try {
    if (isVoiceSupported() && isSpeaking) {
      window.speechSynthesis.cancel();
      isSpeaking = false;
      console.log("🛑 Voice manually stopped");
    }
  } catch (err) {
    console.error("Stop Speech Error:", err);
  }
}

// 🧠 Convert prediction report → spoken text
export function getDiseaseSpeech(d) {
  if (!d) return "";
  let t = "";

  if (d.name || d.age || d.gender) {
    t += "Here is the patient's prediction report. ";
    if (d.name) t += `Patient name is ${d.name}. `;
    if (d.age) t += `Age ${d.age} years. `;
    if (d.gender) t += `Gender ${d.gender}. `;
  }

  if (d.disease) t += `Predicted disease is ${d.disease}. `;
  if (d.description) t += `Description: ${d.description}. `;
  if (d.medicines?.length) t += `Recommended medicines: ${d.medicines.join(", ")}. `;
  if (d.diet?.length) t += `Suggested diet includes ${d.diet.join(", ")}. `;
  if (d.workout?.length) t += `Workout plan: ${d.workout.join(", ")}.`;

  return t.trim();
}

// 🧠 Chatbot speech cleanup
export function getChatbotSpeech(t) {
  if (!t) return "";
  return t.replace(/[*_#]/g, "").replace(/\s+/g, " ").trim();
}

// =====================================================
// 🎤 SPEECH-TO-TEXT (MIC INPUT)
// =====================================================

// Browser support
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let isListening = false;

// Initialize recognition
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    console.log("🎙️ Listening started...");
    document.dispatchEvent(new Event("voice-listen-start"));
  };

  recognition.onend = () => {
    isListening = false;
    console.log("🛑 Listening ended.");
    document.dispatchEvent(new Event("voice-listen-end"));
  };

  recognition.onerror = (e) => {
    console.error("❌ Recognition Error:", e);
    isListening = false;
    document.dispatchEvent(new CustomEvent("voice-listen-error", { detail: e }));
  };

  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript;
console.log("🎧 Recognized:", text);

voiceBuffer = text;   // store speech for later

document.dispatchEvent(new CustomEvent("voice-recognized", { detail: text }));

};
}

// =====================================================
// 🔵 GLOBAL FUNCTIONS (Must be AFTER recognition init)
// =====================================================

window.startListening = () => {
  if (!recognition) {
    alert("Speech Recognition not supported.");
    return;
  }
  stopSpeaking();  // stop TTS before listening
  console.log("🎤 Voice LISTENING started");
  try {
    recognition.start();
  } catch {
    console.log("Recognition already running");
  }
};

window.stopListening = (() => {
  const origStop = () => {
    console.log("🛑 Voice LISTENING stopped");
    if (recognition) recognition.stop();
  };
  return () => {
    origStop();
    const input = document.getElementById("manualSymptoms");
    if (voiceBuffer) {
      input.value = voiceBuffer.trim().replace(/^,|,$/g, "");
    }
  };
})();


// =====================================================
// 🚀 Auto-stop speech on navigation
// =====================================================
window.addEventListener("beforeunload", () => stopSpeaking());
window.addEventListener("click", (e) => {
  if (e.target.matches("button, input, textarea")) stopSpeaking();
});

console.log("✅ Voice Assistant loaded and active");
