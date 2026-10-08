// 回饋：四個頁面共用的「給偵探貓一點意見」對話框，以及送出回饋的函式（首頁的「回報錯誤」也用 sendFeedback）

async function sendFeedback(payload) {
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "送不出去，網路好像打結了，等一下再試。");
  }
}

(() => {
  const dialog = document.getElementById("feedback-dialog");
  const form = document.getElementById("suggest-form");
  if (!dialog || !form) return;
  const box = document.getElementById("suggest-text");
  const status = document.getElementById("suggest-status");
  // 頁尾的「寫下想法」和首頁結果下方的「給我回饋」都會打開它
  for (const btn of document.querySelectorAll("[data-open-feedback]")) {
    btn.addEventListener("click", () => {
      status.textContent = "";
      dialog.showModal();
      box.focus();
    });
  }
  dialog.querySelector("[data-close-feedback]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close(); // 點對話框外面也可以關掉
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!box.value.trim()) {
      status.textContent = "空白的偵探貓看不懂啦，寫點什麼吧。";
      return;
    }
    try {
      await sendFeedback({ kind: "suggestion", message: box.value.trim() });
      box.value = "";
      status.textContent = "收到！偵探貓會認真看，說不定下一版就有了 🐾";
      setTimeout(() => dialog.close(), 1800);
    } catch (err) {
      status.textContent = err.message;
    }
  });
})();
