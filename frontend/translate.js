// 中文翻譯：由網站伺服器上的開源模型（Qwen3-4B）翻成台灣繁體中文，句子只暫存在伺服器記憶體、不存檔。
// 分析結果先顯示，翻譯一句一句補上。伺服器翻譯無法使用時，改用瀏覽器內建的翻譯（Chrome／Edge）。
// 任何一步卡住超過時間上限就放棄，不讓畫面一直等。

(() => {
  const OPTIONS = { sourceLanguage: "en", targetLanguage: "zh-Hant" };
  const UNAVAILABLE = "負責翻譯的同事去吃飯了，等一下再試。";
  const NO_BROWSER = "只有電腦版 Chrome／Edge 能用瀏覽器翻譯。"; // 測試版沒有伺服器翻譯
  let translatorPromise = null;
  let run = 0; // 每次按「分析」加一；舊的翻譯還在跑時，結果不要寫到新的畫面上

  function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms))]);
  }

  // 瀏覽器內建翻譯（備用）。要在使用者按下「分析」的當下呼叫：瀏覽器規定第一次下載翻譯模型時，必須是使用者的操作觸發的
  function prepareBrowser() {
    if (translatorPromise || !("Translator" in self)) return;
    translatorPromise = (async () => {
      const availability = await withTimeout(Translator.availability(OPTIONS), 4000);
      if (availability === "unavailable") return null;
      return withTimeout(Translator.create(OPTIONS), availability === "available" ? 8000 : 120000);
    })().catch(() => null);
  }

  async function browserTranslate(text) {
    prepareBrowser();
    const translator = await translatorPromise;
    if (!translator) {
      translatorPromise = null; // 下次按分析時再試一次
      throw new Error("unsupported");
    }
    return withTimeout(translator.translate(text), 10000);
  }

  // 回傳翻譯；伺服器說次數太多時丟出訊息；伺服器無法翻譯時改用瀏覽器
  async function serverTranslate(text, phrases) {
    if (document.documentElement.dataset.edition === "test") return browserTranslate(text); // 測試版沒有伺服器翻譯
    let response;
    try {
      response = await withTimeout(
        fetch("/api/translate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, phrases }),
        }),
        60000,
      );
    } catch {
      return browserTranslate(text);
    }
    if (response.ok) return (await response.json()).translation;
    if (response.status === 429) {
      const detail = (await response.json().catch(() => ({}))).detail;
      throw new Error(detail || "翻譯次數太多，偵探貓要喘口氣，一分鐘後再來。");
    }
    return browserTranslate(text);
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

  document.getElementById("form").addEventListener("submit", prepareBrowser, { capture: true });

  document.addEventListener("analysis-rendered", async (event) => {
    const { sentences } = event.detail;
    const myRun = ++run;
    const pending = [];
    for (const [i, sentence] of sentences.entries()) {
      const node = document.querySelector(`[data-translation="${i}"]`);
      if (!node || sentence.status === "failed" || sentence.translation) continue;
      setLine(node, "翻譯中…", false, sentence);
      pending.push(i);
    }
    // 一句一句翻：伺服器一次只能翻一句，同時送出也只是排隊
    for (const i of pending) {
      if (myRun !== run) return;
      const sentence = sentences[i];
      try {
        const zh = await serverTranslate(sentence.text, (sentence.phrases || []).map((p) => p.id));
        if (myRun !== run) return;
        sentence.translation = zh; // 重新畫這一句時（例如點片段）不用再翻一次
        const node = document.querySelector(`[data-translation="${i}"]`);
        if (node) setLine(node, zh, true);
      } catch (error) {
        if (myRun !== run) return;
        const node = document.querySelector(`[data-translation="${i}"]`);
        const testEdition = document.documentElement.dataset.edition === "test";
        const message = error.message.includes("次數") ? error.message
          : testEdition && error.message === "unsupported" ? NO_BROWSER : UNAVAILABLE;
        if (node) setLine(node, message, false, sentence);
      }
    }
  });
})();
