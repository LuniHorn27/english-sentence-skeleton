// 1-1 空殼版：送出句子 → 取得分析結果 → 簡單列出標題與片段。
// 正式畫面在 1-2 完成。使用者輸入的文字一律用 textContent 顯示，不當成網頁程式碼。

const form = document.getElementById("form");
const input = document.getElementById("input");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function render(data) {
  result.replaceChildren();
  for (const sentence of data.sentences) {
    result.append(el("div", "header", sentence.header));
    result.append(el("p", null, sentence.text));
    const row = el("div", "chunks");
    for (const chunk of sentence.chunks) {
      const box = el("div", "chunk");
      box.append(el("span", "role", chunk.role === "M" ? chunk.function : chunk.role));
      box.append(el("span", "text", chunk.implicit ? chunk.text : chunk.text));
      row.append(box);
    }
    result.append(row);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  const text = input.value.trim();
  if (!text) {
    showError("請輸入一個英文句子");
    return;
  }
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      showError(typeof body.detail === "string" ? body.detail : "分析失敗，請稍後再試");
      return;
    }
    render(await response.json());
  } catch {
    showError("連不上伺服器，請確認伺服器已啟動");
  }
});
