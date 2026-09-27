// 朗讀：優先使用伺服器上的 Kokoro 開源語音（聲音自然、每台裝置都一樣）；
// 伺服器朗讀失敗時，改用瀏覽器內建語音。
// 提供給 app.js 使用：Speech.available、Speech.speak(text)、Speech.slow（是否慢速）。

window.Speech = (() => {
  const synth = "speechSynthesis" in window ? window.speechSynthesis : null;
  let slow = false;
  let current = null; // 正在播放的聲音
  try { slow = localStorage.getItem("slow") === "1"; } catch { /* 忽略 */ }

  function stop() {
    if (current) {
      current.pause();
      URL.revokeObjectURL(current.src);
      current = null;
    }
    synth?.cancel();
  }

  function speakWithBrowser(text) {
    if (!synth) return;
    const voices = synth.getVoices().filter((v) => v.lang?.toLowerCase().startsWith("en"));
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voices.find((v) => v.lang === "en-US") || voices[0] || null;
    u.lang = u.voice?.lang || "en-US";
    u.rate = slow ? 0.7 : 0.95;
    synth.speak(u);
  }

  async function speak(text) {
    stop();
    try {
      const response = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, speed: slow ? "slow" : "normal" }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const blob = await response.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      current = audio;
      await audio.play();
    } catch {
      speakWithBrowser(text); // 伺服器朗讀失敗 → 瀏覽器內建語音
    }
  }

  return {
    available: true,
    speak,
    get slow() { return slow; },
    set slow(value) {
      slow = value;
      try { localStorage.setItem("slow", value ? "1" : "0"); } catch { /* 忽略 */ }
    },
  };
})();
