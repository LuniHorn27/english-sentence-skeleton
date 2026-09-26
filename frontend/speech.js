// 朗讀（2-3）：使用瀏覽器內建的語音（Web Speech API），免費、不用連外部服務。
// 提供給 app.js 使用：Speech.available、Speech.speak(text)、Speech.slow（是否慢速）。

window.Speech = (() => {
  const synth = "speechSynthesis" in window ? window.speechSynthesis : null;
  let voice = null;
  let slow = false;
  try { slow = localStorage.getItem("slow") === "1"; } catch { /* 忽略 */ }

  function pickVoice() {
    if (!synth) return;
    const voices = synth.getVoices().filter((v) => v.lang && v.lang.toLowerCase().startsWith("en"));
    // 優先選美式英文、再來是英式，其次任何英文聲音
    voice = voices.find((v) => v.lang === "en-US" && v.localService) || voices.find((v) => v.lang === "en-US")
      || voices.find((v) => v.lang === "en-GB") || voices[0] || null;
  }
  if (synth) {
    pickVoice();
    synth.addEventListener?.("voiceschanged", pickVoice);
  }

  function speak(text) {
    if (!synth) return;
    synth.cancel(); // 先停掉上一段，避免疊在一起
    const u = new SpeechSynthesisUtterance(text);
    u.lang = voice?.lang || "en-US";
    if (voice) u.voice = voice;
    u.rate = slow ? 0.7 : 0.95;
    synth.speak(u);
  }

  return {
    available: Boolean(synth),
    speak,
    get slow() { return slow; },
    set slow(value) {
      slow = value;
      try { localStorage.setItem("slow", value ? "1" : "0"); } catch { /* 忽略 */ }
    },
  };
})();
