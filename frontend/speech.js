// 朗讀：優先使用伺服器上的 Kokoro 開源語音（聲音自然、每台裝置都一樣）；
// 伺服器不能朗讀時（例如測試版），改用瀏覽器內建語音。
// 手機（尤其 iPhone）規定朗讀要在使用者按下的當下開始，先等伺服器回應再改用瀏覽器語音就會被擋、沒有聲音，
// 所以網頁一打開就先問伺服器能不能朗讀；不能的話，按下去直接用瀏覽器語音。
// 提供給 app.js 使用：Speech.available、Speech.speak(text)、Speech.slow（是否慢速）。

window.Speech = (() => {
  const synth = "speechSynthesis" in window ? window.speechSynthesis : null;
  let slow = false;
  // 只用一個播放器：按下的當下先放一段無聲的聲音「解鎖」它，等伺服器的聲音回來再換上去，iPhone 才肯播
  const player = new Audio();
  const SILENCE = "data:audio/wav;base64,UklGRjQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YRAAAAAAAAAAAAAAAAAAAAAAAAAA";
  let blobUrl = null; // 正在播放的伺服器聲音
  let serverVoice = true; // 還不知道時先試伺服器
  let turn = 0; // 每按一次加一；前一次還沒唸完就按下一句時，前一次的結果不要再出聲

  fetch("/api/site")
    .then((r) => (r.ok ? r.json() : {}))
    .then((site) => {
      if (site.tts === false) serverVoice = false;
    })
    .catch(() => { /* 拿不到就照原本的順序：先伺服器、失敗再用瀏覽器 */ });

  // 有些瀏覽器（iPhone、Chrome）第一次問語音清單會拿到空的，先問一次讓它準備好
  synth?.getVoices();
  synth?.addEventListener?.("voiceschanged", () => synth.getVoices());

  function stop() {
    player.pause();
    if (blobUrl) {
      URL.revokeObjectURL(blobUrl);
      blobUrl = null;
    }
    synth?.cancel();
  }

  function speakWithBrowser(text) {
    if (!synth) return;
    const voices = synth.getVoices().filter((v) => v.lang?.replace("_", "-").toLowerCase().startsWith("en"));
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voices.find((v) => v.lang.replace("_", "-") === "en-US") || voices[0] || null;
    u.lang = "en-US"; // 沒有找到英文語音時，也要讓瀏覽器用英文唸
    u.rate = slow ? 0.7 : 0.95;
    synth.speak(u);
  }

  async function speak(text) {
    stop();
    const myTurn = ++turn;
    if (!serverVoice) {
      speakWithBrowser(text); // 不經過等待，手機才不會擋
      return;
    }
    player.src = SILENCE;
    player.play().catch(() => { /* 解鎖失敗也沒關係，後面還有瀏覽器語音 */ });
    try {
      const response = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, speed: slow ? "slow" : "normal" }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const blob = await response.blob();
      if (myTurn !== turn) return;
      if (blobUrl) URL.revokeObjectURL(blobUrl); // 連按兩次時，前一次的聲音不要留著
      blobUrl = URL.createObjectURL(blob);
      player.src = blobUrl;
      await player.play();
    } catch (error) {
      if (myTurn !== turn || error?.name === "AbortError") return; // 已經按了別句
      // 伺服器不能朗讀 → 之後直接用瀏覽器語音。只是手機不讓播放（NotAllowedError）時，伺服器其實沒壞，下次照樣用伺服器
      if (error?.name !== "NotAllowedError") serverVoice = false;
      speakWithBrowser(text);
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
