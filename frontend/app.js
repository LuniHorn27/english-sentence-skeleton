// 英文句子骨架分析：前端畫面
// 資安：句子、說明等文字一律用 textContent 顯示；只有我們自己寫的文法重點卡允許 <b> 粗體。

const MAX_CHARS = 2000;
const GROUP = { S: "S", RS: "S", Vt: "V", Vi: "V", V: "V", aux: "V", O: "O", IO: "O", DO: "O", SC: "C", OC: "C" };
const LABEL = { aux: "aux.", RS: "真主詞", conj: "conj.", unknown: "未分析" };
const ROLE_NAME = {
  S: "主詞", RS: "真主詞", Vt: "及物動詞", Vi: "不及物動詞", V: "動詞", aux: "助動詞",
  O: "受詞", IO: "間接受詞", DO: "直接受詞", SC: "主詞補語", OC: "受詞補語",
  conj: "連接詞", unknown: "未分析",
};
const CLAUSE_NAME = ["子句一", "子句二", "子句三", "子句四"];
const CALLOUT = {
  formula: ["📍", "公式", "c-formula"],
  tip: ["💡", "小技巧", "c-tip"],
  warn: ["⚠️", "常見錯誤", "c-warn"],
  info: ["ℹ", "補充", "c-info"],
};

const $ = (id) => document.getElementById(id);
const form = $("form");
const input = $("input");
const submit = $("submit");
const counter = $("counter");
const errorBox = $("error");
const toolbar = $("toolbar");
const result = $("result");

let sentences = [];      // 目前顯示的分析結果
let views = [];          // 每一句的畫面狀態：選到哪個片段、展開哪些子句、打開哪些卡
const cardCache = new Map();

// ---------- 小工具 ----------
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

// 文法重點卡是我們自己寫的內容，只保留 <b>，其餘一律跳脫
function safeHTML(text) {
  const escaped = String(text)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  return escaped.replace(/&lt;(\/?)b&gt;/g, "<$1b>");
}

function storageGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch { /* 無痕模式等情況，不影響使用 */ }
}

// ---------- 顯示模式 ----------
function setMode(mode) {
  result.classList.toggle("detail", mode === "detail");
  for (const btn of toolbar.querySelectorAll("[data-mode]")) {
    btn.setAttribute("aria-pressed", String(btn.dataset.mode === mode));
  }
  storageSet("mode", mode);
}
toolbar.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-mode]");
  if (btn) setMode(btn.dataset.mode);
});
setMode(storageGet("mode") === "detail" ? "detail" : "skeleton");

// ---------- 片段 ----------
function chunkText(chunk) {
  // 把核心字包成粗體，其他照原樣
  const tx = el("span", "tx");
  if (chunk.implicit) {
    tx.textContent = chunk.text;
    return tx;
  }
  const heads = [...(chunk.heads || [])].sort((a, b) => a.start - b.start);
  let pos = chunk.start;
  for (const h of heads) {
    if (h.start > pos) tx.append(chunk.text.slice(pos - chunk.start, h.start - chunk.start));
    const hw = el("span", "hw", h.text);
    hw.append(el("span", "hw-mark", "核心"));
    tx.append(hw);
    pos = h.end;
  }
  if (pos < chunk.end) tx.append(chunk.text.slice(pos - chunk.start));
  return tx;
}

function labelText(chunk) {
  if (chunk.role === "M") {
    return chunk.modifies ? `${chunk.function} ${chunk.modifies.text}` : chunk.function;
  }
  return LABEL[chunk.role] || chunk.role;
}

function roleClass(chunk) {
  if (chunk.role === "M") return "m";
  if (chunk.role === "conj") return "conj";
  if (chunk.role === "unknown") return "unk";
  const style = chunk.role === "aux" || chunk.role === "RS" ? "soft" : "core";
  return `${style} r-${GROUP[chunk.role]}`;
}

function miniChunk(chunk) {
  const node = el("span", `ck ${roleClass(chunk)}`);
  node.append(el("span", "lb", labelText(chunk)), el("span", "tx", chunk.text));
  return node;
}

function chunkNode(sIdx, chunk, trailing) {
  const view = views[sIdx];
  const node = el("button", `ck ${roleClass(chunk)}`);
  node.type = "button";
  if (view.selected === chunk.id) node.classList.add("selected");
  node.setAttribute("aria-label", `${chunk.text}：${chunk.role === "M" ? labelText(chunk) : ROLE_NAME[chunk.role]}`);
  node.append(el("span", "lb", labelText(chunk)));

  const expanded = chunk.inner?.length && view.expanded.has(chunk.id);
  if (expanded) {
    const inner = el("span", "inner");
    chunk.inner.forEach((c) => inner.append(miniChunk(c)));
    const wrap = el("span", "inner-wrap");
    wrap.append(inner);
    if (trailing) wrap.append(el("span", "punct tx", trailing));
    node.append(wrap);
  } else {
    const tx = chunkText(chunk);
    if (trailing) tx.append(el("span", "punct", trailing));
    node.append(tx);
  }
  node.append(el("span", "sub", chunk.inner?.length ? (expanded ? "收合子句" : "點我展開子句") : ""));

  node.addEventListener("click", () => {
    if (chunk.inner?.length) {
      view.expanded.has(chunk.id) ? view.expanded.delete(chunk.id) : view.expanded.add(chunk.id);
    }
    view.selected = view.selected === chunk.id && !chunk.inner?.length ? null : chunk.id;
    renderSentence(sIdx);
  });
  return node;
}

// 片段之間的標點（逗號、句號）接在前一個片段後面顯示
function trailingPunct(sentence, chunks, i) {
  const c = chunks[i];
  if (c.implicit) return "";
  const next = chunks.slice(i + 1).find((x) => !x.implicit);
  const gap = sentence.text.slice(c.end, next ? next.start : sentence.text.length).trim();
  return gap;
}

function chunkRow(sIdx) {
  const sentence = sentences[sIdx];
  const row = el("div", "row");
  const chunks = sentence.chunks;
  const nodes = chunks.map((c, i) => chunkNode(sIdx, c, trailingPunct(sentence, chunks, i)));

  if (sentence.kind !== "compound") {
    row.append(...nodes);
    return row;
  }
  // 對等句：同一個子句的片段圈在同一個框裡，連接詞放在框外
  let box = null;
  let boxClause = null;
  chunks.forEach((c, i) => {
    if (c.role === "conj") {
      box = null;
      row.append(nodes[i]);
      return;
    }
    if (!box || boxClause !== c.clause) {
      box = el("div", "clause");
      box.append(el("span", "clause-cap", CLAUSE_NAME[c.clause] || `子句 ${c.clause + 1}`));
      box.append(el("div", "clause-row"));
      boxClause = c.clause;
      row.append(box);
    }
    box.lastChild.append(nodes[i]);
  });
  return row;
}

// ---------- 朗讀 ----------
function speakButton(text, label, extra = "") {
  const btn = el("button", `speak ${extra}`, `🔊 ${label}`);
  btn.type = "button";
  btn.setAttribute("aria-label", `${label}：${text}`);
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    window.Speech.speak(text);
  });
  return btn;
}

// ---------- 說明 ----------
function explainBox(sentence, view) {
  const chunk = sentence.chunks.find((c) => c.id === view.selected);
  if (!chunk) return null;
  const box = el("div", "explain");
  box.append(el("strong", null, chunk.text));
  const kind = chunk.role === "M" ? labelText(chunk) : `${ROLE_NAME[chunk.role]}（${LABEL[chunk.role] || chunk.role}）`;
  box.append(document.createTextNode(`　${kind}`));
  if (chunk.structure) box.append(el("span", "struct", `　結構：${chunk.structure}`));
  if (window.Speech?.available && !chunk.implicit) {
    box.append(speakButton(chunk.text, "唸這一段", "speak-mini"));
  }
  if (chunk.note) {
    box.append(el("br"));
    box.append(document.createTextNode(chunk.note));
  }
  return box;
}

// ---------- 文法重點卡 ----------
function fetchCard(id) {
  if (!cardCache.has(id)) {
    cardCache.set(id, fetch(`/api/cards/${encodeURIComponent(id)}`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
  }
  return cardCache.get(id);
}

function fillVars(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, k) => (vars && k in vars ? vars[k] : ""));
}

function examplesList(examples) {
  const ul = el("ul", "examples");
  for (const ex of examples) {
    const li = el("li");
    if (ex.mark === "ok") li.append(el("span", "mark-ok", "✓ "));
    else if (ex.mark === "no") li.append(el("span", "mark-no", "✗ "));
    else li.append("・");
    const en = el("span", "en");
    en.innerHTML = safeHTML(ex.en);
    li.append(en);
    if (ex.zh) li.append(el("span", "zh-note", ex.zh));
    ul.append(li);
  }
  return ul;
}

function cardBlock(block) {
  if (block.type === "heading") return el("h4", null, block.text);
  if (block.type === "list") {
    const ul = el("ul");
    for (const item of block.items) {
      const li = el("li");
      li.innerHTML = safeHTML(item);
      ul.append(li);
    }
    return ul;
  }
  if (block.type === "examples") return examplesList(block.examples);
  const [icon, name, cls] = CALLOUT[block.type];
  const box = el("div", `callout ${cls}`);
  box.append(el("span", "icon", icon));
  const body = el("div");
  body.append(el("span", "c-name", name));
  const text = el("span", "c-text");
  text.innerHTML = safeHTML(block.text);
  body.append(text);
  if (block.examples?.length) body.append(examplesList(block.examples));
  box.append(body);
  return box;
}

function cardNode(sIdx, ref, card) {
  const view = views[sIdx];
  const open = view.openCards.has(ref.id);
  const node = el("div", open ? "card open" : "card"); // 展開的卡片在寬螢幕上佔滿整行
  const head = el("div", "card-head");
  head.append(el("span", "card-tag", "文法重點"), el("span", "card-title", card.title));
  const brief = el("span", "card-brief");
  brief.innerHTML = safeHTML(fillVars(card.brief, ref.vars));
  const toggle = el("button", "card-toggle", open ? "收合" : "詳細說明");
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", String(open));
  toggle.addEventListener("click", () => {
    open ? view.openCards.delete(ref.id) : view.openCards.add(ref.id);
    renderSentence(sIdx);
  });
  head.append(brief, toggle);
  node.append(head);
  if (open) {
    const body = el("div", "card-body");
    card.blocks.forEach((b) => body.append(cardBlock(b)));
    node.append(body);
  }
  return node;
}

// ---------- 片語（清單在 backend/analyzer/phrases.yaml） ----------
function phraseCard(sentence) {
  const node = el("div", "card phrases");
  const head = el("div", "card-head");
  head.append(el("span", "card-tag phrase-tag", "片語"));
  node.append(head);
  const list = el("ul", "phrase-list");
  for (const p of sentence.phrases) {
    const li = el("li");
    const line = el("div", "phrase-line");
    line.append(el("b", "phrase-en", p.phrase), el("span", "phrase-mean", p.meaning), el("span", "phrase-kind", p.kind));
    li.append(line);
    if (p.literal) li.append(el("div", "phrase-note", `字面是「${p.literal}」，不能照字面翻。`));
    if (p.note) li.append(el("div", "phrase-note", p.note));
    list.append(li);
  }
  node.append(list);
  return node;
}

// ---------- 回報錯誤（2-5） ----------
async function sendFeedback(payload) {
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "送出失敗，請稍後再試");
  }
}

function feedbackForm(sIdx) {
  const sentence = sentences[sIdx];
  const view = views[sIdx];
  const form = el("form", "feedback");
  form.append(el("p", "fb-title", "哪裡分析錯了？"));

  const select = el("select");
  select.setAttribute("aria-label", "選擇有問題的部分");
  const options = [["句型", sentence.header || "（無）"]];
  for (const c of sentence.chunks) {
    options.push([`「${c.text}」`, c.role === "M" ? labelText(c) : `${ROLE_NAME[c.role]}（${LABEL[c.role] || c.role}）`]);
  }
  for (const p of sentence.phrases || []) options.push([`片語「${p.phrase}」`, p.meaning]);
  options.push(["文法重點卡", ""], ["中文翻譯", sentence.translation || ""], ["其他", ""]);
  for (const [part, current] of options) {
    const opt = el("option", null, current ? `${part}：${current}` : part);
    opt.value = JSON.stringify([part, current]);
    select.append(opt);
  }

  const text = el("textarea");
  text.rows = 2;
  text.maxLength = 1000;
  text.placeholder = "你認為正確的是什麼？例如：in the garden 應該是副詞・表地點";
  text.setAttribute("aria-label", "你認為正確的答案");
  const note = el("p", "fb-note", "請不要填寫姓名、電話等個人資料。");
  const status = el("p", "fb-status");
  const send = el("button", "primary", "送出");
  send.type = "submit";
  form.append(select, text, note, send, status);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!text.value.trim()) {
      status.textContent = "請先寫下你認為正確的答案";
      return;
    }
    const [part, current] = JSON.parse(select.value);
    send.disabled = true;
    try {
      await sendFeedback({ kind: "error", sentence: sentence.text, part, current, message: text.value.trim(), analysis: sentence });
      view.feedback = "sent";
      renderSentence(sIdx);
    } catch (err) {
      status.textContent = err.message;
      send.disabled = false;
    }
  });
  return form;
}

// ---------- 提供建議（頁尾） ----------
const suggestForm = $("suggest-form");
if (suggestForm) {
  suggestForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const box = $("suggest-text");
    const status = $("suggest-status");
    if (!box.value.trim()) {
      status.textContent = "請先寫下你的建議";
      return;
    }
    try {
      await sendFeedback({ kind: "suggestion", message: box.value.trim() });
      box.value = "";
      status.textContent = "收到了，謝謝你的建議！";
    } catch (err) {
      status.textContent = err.message;
    }
  });
}

// ---------- 一整句 ----------
function renderSentence(sIdx) {
  const sentence = sentences[sIdx];
  const view = views[sIdx];
  const box = view.node;
  box.replaceChildren();

  const head = el("div", "s-head");
  if (sentences.length > 1) head.append(el("span", "s-num", String(sIdx + 1)));
  if (sentence.kind === "compound") head.append(el("span", "tag", "對等句"));
  if (sentence.clauses.length) {
    // 句型標籤可以點，打開五大句型介紹的對應段落
    const link = el("a", "pattern", sentence.header);
    link.href = `/patterns#p${sentence.clauses[0].pattern}`;
    link.target = "_blank";
    link.rel = "noopener";
    link.title = "看這個句型的說明";
    head.append(link);
  }
  // 動詞句型字典檢查不通過：提醒這句可能分析錯了（點開看原因）
  const doubts = sentence.clauses.map((c) => c.doubt).filter(Boolean);
  if (doubts.length) {
    const flag = el("button", "doubt", "⚠️ 這句可能分析錯了");
    flag.type = "button";
    flag.setAttribute("aria-expanded", String(Boolean(view.doubtOpen)));
    flag.addEventListener("click", () => {
      view.doubtOpen = !view.doubtOpen;
      renderSentence(sIdx);
    });
    head.append(flag);
  }
  const tools = el("span", "s-tools");
  if (window.Speech?.available && sentence.status !== "failed") {
    tools.append(speakButton(sentence.text, "朗讀"));
  }
  const report = el("button", "speak", view.feedback === "sent" ? "已回報，謝謝" : "回報錯誤");
  report.type = "button";
  report.disabled = view.feedback === "sent";
  report.addEventListener("click", () => {
    view.feedback = view.feedback === "open" ? null : "open";
    renderSentence(sIdx);
  });
  tools.append(report);
  head.append(tools);
  box.append(head);
  if (doubts.length && view.doubtOpen) {
    box.append(el("div", "banner doubt-note", `${doubts.join(" ")}如果你知道正確答案，歡迎按「回報錯誤」告訴我們。`));
  }

  if (sentence.status === "failed" && sentences.length > 1) box.append(el("p", "failed-text", sentence.text));
  if (sentence.status !== "ok" && sentence.message) {
    box.append(el("div", `banner${sentence.status === "failed" ? " fail" : ""}`, sentence.message));
  }
  if (sentence.status !== "failed") box.append(chunkRow(sIdx));

  const zh = el("p", "zh");
  zh.dataset.translation = String(sIdx);
  if (sentence.translation) {
    zh.textContent = sentence.translation;
    zh.append(el("span", "mt", "機器翻譯"));
  } else if (sentence.translationStatus) {
    zh.append(el("span", "zh-status", sentence.translationStatus));
  }
  box.append(zh);

  const explain = explainBox(sentence, view);
  if (explain) box.append(explain);

  if (view.feedback === "open") box.append(feedbackForm(sIdx));

  const cardsWrap = el("div", "cards");
  box.append(cardsWrap);
  if (sentence.phrases?.length) cardsWrap.append(phraseCard(sentence));
  for (const ref of sentence.cards || []) {
    const slot = el("div");
    cardsWrap.append(slot);
    fetchCard(ref.id).then((card) => {
      if (card) slot.replaceWith(cardNode(sIdx, ref, card));
      else slot.remove();
    });
  }
}

function render(data) {
  sentences = data.sentences;
  result.replaceChildren();
  // 3 句以上：最上方放「句子目錄」，點編號就跳到那一句
  if (sentences.length > 2) {
    const nav = el("nav", "s-nav");
    nav.setAttribute("aria-label", "句子目錄");
    nav.append(el("span", "s-nav-title", `共 ${sentences.length} 句`));
    sentences.forEach((s, i) => {
      const a = el("a", "s-nav-item");
      a.href = `#s${i + 1}`;
      a.title = s.text;
      a.append(el("span", "s-nav-num", String(i + 1)), el("span", "s-nav-text", s.text));
      nav.append(a);
    });
    result.append(nav);
  }
  views = sentences.map((_, i) => {
    const node = el("article", "sentence");
    node.id = `s${i + 1}`;
    result.append(node);
    return { node, selected: null, expanded: new Set(), openCards: new Set(), feedback: null };
  });
  sentences.forEach((_, i) => renderSentence(i));
  toolbar.hidden = false;
  $("result-actions").hidden = false;
  document.dispatchEvent(new CustomEvent("analysis-rendered", { detail: { sentences } }));
}

// ---------- 輸入 ----------
function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function updateCounter() {
  const n = input.value.length;
  counter.textContent = `${n} / ${MAX_CHARS}`;
  counter.classList.toggle("over", n > MAX_CHARS);
}
input.addEventListener("input", () => {
  updateCounter();
  errorBox.hidden = true;
});
input.addEventListener("keydown", (e) => {
  // Enter 送出；Shift＋Enter 換行；中文輸入法選字時的 Enter 不送出
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  const text = input.value.trim();
  if (!text) return showError("請輸入英文句子或一段英文文章");
  if (text.length > MAX_CHARS) return showError(`句子太長了，請控制在 ${MAX_CHARS} 個字元以內`);

  submit.disabled = true;
  submit.textContent = "分析中…";
  result.replaceChildren(el("p", "loading", "分析中，請稍候…"));
  $("result-actions").hidden = true;
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      result.replaceChildren();
      showError(typeof body.detail === "string" ? body.detail : "分析失敗，請稍後再試");
      return;
    }
    render(await response.json());
    addHistory(text);
  } catch {
    result.replaceChildren();
    showError("連不上伺服器，請確認伺服器已啟動");
  } finally {
    submit.disabled = false;
    submit.textContent = "分析";
  }
});

// ---------- 分享（F6） ----------
// 分享某一句的分析時，句子放在網址的 # 後面：這部分不會送到伺服器
const toast = $("toast");
function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 2500);
}

async function share(url, title) {
  if (navigator.share) {
    try {
      await navigator.share({ title, url });
      return;
    } catch (err) {
      if (err.name === "AbortError") return; // 使用者自己取消
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    showToast("已複製連結，可以貼給朋友了");
  } catch {
    window.prompt("請複製這個連結：", url);
  }
}

$("share-site").addEventListener("click", () => share(location.origin + "/", "英文句子骨架分析"));
$("share-result").addEventListener("click", () => {
  const text = input.value.trim();
  if (!text) return;
  share(`${location.origin}/#q=${encodeURIComponent(text)}`, "英文句子骨架分析");
});

// 從分享連結打開：自動填入句子並分析
function loadFromHash() {
  const m = location.hash.match(/^#q=(.+)$/);
  if (!m) return;
  try {
    input.value = decodeURIComponent(m[1]).slice(0, MAX_CHARS);
  } catch {
    return;
  }
  updateCounter();
  form.requestSubmit();
}
window.addEventListener("hashchange", loadFromHash);

// ---------- 列印講義 ----------
// 列印時用詳細模式（修飾語標籤也印出來），印完再切回原本的模式
let modeBeforePrint = null;
window.addEventListener("beforeprint", () => {
  modeBeforePrint = result.classList.contains("detail") ? "detail" : "skeleton";
  result.classList.add("detail");
});
window.addEventListener("afterprint", () => {
  if (modeBeforePrint) setMode(modeBeforePrint);
});
$("print").addEventListener("click", () => window.print());

// ---------- 最近分析（只存在這台裝置的瀏覽器裡） ----------
const HISTORY_MAX = 10;
function loadHistory() {
  try { return JSON.parse(storageGet("history") || "[]").filter((x) => typeof x === "string"); } catch { return []; }
}
function renderHistory() {
  const items = loadHistory();
  const wrap = $("history");
  const list = $("history-list");
  list.replaceChildren();
  wrap.hidden = items.length === 0;
  $("history-count").textContent = `（${items.length}）`;
  for (const text of items) {
    const li = el("li");
    const item = el("button", "history-item", text); // 太長的句子由 CSS 截成一行「…」
    item.type = "button";
    item.title = text;
    item.addEventListener("click", () => {
      input.value = text;
      updateCounter();
      wrap.open = false;
      form.requestSubmit();
    });
    li.append(item);
    list.append(li);
  }
}
function addHistory(text) {
  const items = [text, ...loadHistory().filter((x) => x !== text)].slice(0, HISTORY_MAX);
  storageSet("history", JSON.stringify(items));
  renderHistory();
}
$("history-clear").addEventListener("click", () => {
  storageSet("history", "[]");
  renderHistory();
});

updateCounter();
renderHistory();
loadFromHash();
