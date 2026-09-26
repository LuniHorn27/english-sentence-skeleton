// 中文翻譯（1-8）：使用瀏覽器內建的翻譯功能（Chrome／Edge 的 Translator API）。
// 翻譯在使用者自己的電腦上進行，句子不會送到外部伺服器，也不用付費。
// 不支援的瀏覽器顯示提示；任何一步卡住超過時間上限，都當作不支援，不讓畫面一直等。

(() => {
  const OPTIONS = { sourceLanguage: "en", targetLanguage: "zh-Hant" };
  const UNSUPPORTED = "目前的瀏覽器不支援自動翻譯，請使用電腦版 Chrome 或 Edge。";
  let translatorPromise = null;

  function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms))]);
  }

  // 要在使用者按下「分析」的當下呼叫：瀏覽器規定第一次下載翻譯模型時，必須是使用者的操作觸發的
  function prepare() {
    if (translatorPromise || !("Translator" in self)) return;
    translatorPromise = (async () => {
      const availability = await withTimeout(Translator.availability(OPTIONS), 4000);
      if (availability === "unavailable") return null;
      return withTimeout(Translator.create(OPTIONS), availability === "available" ? 8000 : 120000);
    })().catch(() => null);
  }

  function setLine(node, text, isTranslation, sentence) {
    if (sentence && !isTranslation) sentence.translationStatus = text; // 重新畫這一句時保留提示
    node.replaceChildren();
    if (isTranslation) {
      node.append(text);
      const mt = document.createElement("span");
      mt.className = "mt";
      mt.textContent = "機器翻譯";
      node.append(mt);
    } else {
      const note = document.createElement("span");
      note.className = "zh-status";
      note.textContent = text;
      node.append(note);
    }
  }

  document.getElementById("form").addEventListener("submit", prepare, { capture: true });

  document.addEventListener("analysis-rendered", async (event) => {
    const { sentences } = event.detail;
    for (const [i, sentence] of sentences.entries()) {
      const node = document.querySelector(`[data-translation="${i}"]`);
      if (!node || sentence.status === "failed" || sentence.translation) continue;
      if (!("Translator" in self)) {
        setLine(node, UNSUPPORTED, false, sentence);
        continue;
      }
      setLine(node, "翻譯中…", false, sentence);
      prepare();
      const translator = await translatorPromise;
      if (!translator) {
        translatorPromise = null; // 下次按分析時再試一次
        setLine(node, UNSUPPORTED, false, sentence);
        continue;
      }
      try {
        const zh = await withTimeout(translator.translate(sentence.text), 10000);
        sentence.translation = zh; // 重新畫這一句時（例如點片段）不用再翻一次
        setLine(node, zh, true);
      } catch {
        setLine(node, "翻譯失敗，請稍後再試。", false, sentence);
      }
    }
  });
})();
