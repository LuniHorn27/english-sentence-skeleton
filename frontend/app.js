// 英文句子骨架分析：前端畫面
// 資安：句子、說明等文字一律用 textContent 顯示；只有我們自己寫的文法重點卡允許 <b> 粗體。

const MAX_CHARS = 2000;
const GROUP = { S: "S", RS: "S", RO: "O", Vt: "V", Vi: "V", V: "V", aux: "V", O: "O", IO: "O", DO: "O", SC: "C", OC: "C" };
const LABEL = { V: "Vi", aux: "aux.", RS: "真主詞", RO: "真受詞", EF: "強調框架", conj: "conj.", unknown: "未分析" };
const ROLE_NAME = {
  S: "主詞", RS: "真主詞", RO: "真受詞", Vt: "及物動詞", Vi: "不及物動詞", V: "不及物動詞（連綴動詞）", aux: "助動詞",
  O: "受詞", IO: "間接受詞", DO: "直接受詞", SC: "主詞補語", OC: "受詞補語",
  EF: "強調句框架", conj: "連接詞", unknown: "未分析",
};
const CLAUSE_NAME = ["子句一", "子句二", "子句三", "子句四"];
const CALLOUT = {
  formula: ["📍", "公式", "c-formula"],
  tip: ["💡", "小技巧", "c-tip"],
  warn: ["⚠️", "常見錯誤", "c-warn"],
  info: ["ℹ", "補充", "c-info"],
};

// 線條圖示（直接畫在網頁裡，不另外載入圖示字型）
const ICON = {
  volume: '<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z"/><path d="M15.5 9.5a3.5 3.5 0 0 1 0 5M18 7a7 7 0 0 1 0 10"/>',
  flag: '<path d="M5.5 20.5V4M5.5 4.5h11l-2.5 4 2.5 4h-11"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 4.5l8.5 15h-17z"/><path d="M12 10v4M12 16.8v.2"/>',
  pencil: '<path d="M4.5 19.5l1-4.5L16 4.5l3.5 3.5L9 18.5z"/><path d="M14 6.5l3.5 3.5"/>',
};
function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${ICON[name]}</svg>`;
  return t.content.firstChild;
}

// 偵探貓：同一隻貓，只換放大鏡裡的眼睛（品牌規範：不加嘴巴和腮紅）
const CAT_FACE = '<rect width="64" height="64" rx="14" fill="#2f6fed"/><path d="M10 33 L11 9 L24 19 Q32 16.5 40 19 L53 9 L54 33 Q55 53 32 55 Q9 53 10 33Z" fill="#fff"/><ellipse cx="22" cy="33" rx="3" ry="3.6" fill="#1a1d23"/><path d="M30 40.5 h4 l-2 2.5z" fill="#e88aa0"/><line x1="48" y1="39" x2="58" y2="50" stroke="#1a1d23" stroke-width="4.5" stroke-linecap="round"/><circle cx="41" cy="31" r="10" fill="#fdf3e1" stroke="#1a1d23" stroke-width="3.5"/>';
const CAT_EYE = {
  idle: '<g class="cat-eye"><ellipse cx="41" cy="32" rx="5" ry="6" fill="#1a1d23"/><circle cx="43" cy="29.5" r="1.7" fill="#fff"/></g>',
  oops: '<path d="M37.6 28.4a3.5 3.5 0 1 1 5.1 3.1c-1.2.6-1.7 1.3-1.7 2.7" fill="none" stroke="#1a1d23" stroke-width="2.6" stroke-linecap="round"/><circle cx="41" cy="38" r="1.5" fill="#1a1d23"/>',
};
function cat(mood = "idle") {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="cat cat-${mood}" viewBox="0 0 64 64" aria-hidden="true">${CAT_FACE}${CAT_EYE[mood === "oops" ? "oops" : "idle"]}</svg>`;
  return t.content.firstChild;
}

// 首頁還沒輸入時顯示的範例（直接寫在網頁裡，不用等伺服器）
const SAMPLE = { sentences: [{
  text: "The teacher showed us a picture.", status: "ok", message: null, kind: "simple",
  clauses: [{ index: 0, pattern: 4, doubt: null }],
  header: "句型五：S + Vt + IO + DO",
  chunks: [
    { id: 0, text: "The teacher", start: 0, end: 11, role: "S", heads: [{ start: 4, end: 11, text: "teacher" }], structure: "名詞片語", note: "主詞，核心字是 teacher。", clause: 0, inner: [] },
    { id: 1, text: "showed", start: 12, end: 18, role: "Vt", heads: [], note: "動詞，後面接兩個受詞：給「誰」（IO）什麼東西（DO）。", clause: 0, inner: [] },
    { id: 2, text: "us", start: 19, end: 21, role: "IO", heads: [], structure: "代名詞", note: "間接受詞：動作給「誰」？", clause: 0, inner: [] },
    { id: 3, text: "a picture", start: 22, end: 31, role: "DO", heads: [{ start: 24, end: 31, text: "picture" }], structure: "名詞片語", note: "直接受詞：給「什麼」？核心字是 picture。", clause: 0, inner: [] },
  ],
  cards: [{ id: "dative_verbs", vars: {} }], phrases: [], typos: [],
  translation: "老師給我們看了一張圖片。",
}] };

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
// 標籤比底下的字寬時（副詞・表時間 ＋ Finally,），讓標籤超出字的寬度、不把片段撐開；
// 只有相鄰兩個標籤真的會重疊時，才把後面的片段往右推一點（使用者回報「空兩格」，2026-10-01）
function fixLabelOverlap(root = result) {
  const chunks = [...root.querySelectorAll(".ck")].filter((c) => c.querySelector(":scope > .lb"));
  for (const c of chunks) c.style.marginLeft = "";
  let prev = null;
  for (const c of chunks) {
    const lb = c.querySelector(":scope > .lb");
    if (getComputedStyle(lb).visibility === "hidden" || !lb.textContent) continue;
    const r = lb.getBoundingClientRect();
    const sameLine = prev && Math.abs(prev.top - r.top) < 4 && prev.parent === c.parentElement;
    if (sameLine && r.left < prev.right + 6) {
      c.style.marginLeft = `${prev.right + 6 - r.left}px`;
    } else if (!sameLine) {
      const left = c.parentElement.getBoundingClientRect().left;  // 每行第一個片段：標籤不要超出左邊
      if (r.left < left) c.style.marginLeft = `${left - r.left}px`;
    }
    const r2 = lb.getBoundingClientRect();
    prev = { top: r2.top, right: r2.right, parent: c.parentElement };
  }
}
let overlapTimer = null;
function scheduleOverlapFix() {
  cancelAnimationFrame(overlapTimer);
  overlapTimer = requestAnimationFrame(() => fixLabelOverlap());
}
window.addEventListener("resize", scheduleOverlapFix);

function setMode(mode) {
  result.classList.toggle("detail", mode === "detail");
  scheduleOverlapFix();
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
  if (chunk.suffix) tx.append(el("span", "suffix", chunk.suffix)); // Let's 的 's（us）
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
  if (chunk.role === "conj" || chunk.role === "EF") return "conj";
  if (chunk.role === "unknown") return "unk";
  const style = chunk.role === "aux" || chunk.role === "RS" || chunk.role === "RO" ? "soft" : "core";
  return `${style} r-${GROUP[chunk.role]}`;
}

// S、Vt、IO 這類兩個字以內的主要成分標籤畫成圓形（2026-10-06 改版）
function makeLabel(chunk) {
  const text = labelText(chunk) || "";
  return el("span", GROUP[chunk.role] && text.length <= 2 ? "lb dot" : "lb", text);
}

function miniChunk(chunk) {
  const node = el("span", `ck ${roleClass(chunk)}`);
  node.append(makeLabel(chunk), el("span", "tx", chunk.text + (chunk.suffix || "")));
  return node;
}

function chunkNode(sIdx, chunk, trailing) {
  const view = views[sIdx];
  const node = el("button", `ck ${roleClass(chunk)}`);
  node.type = "button";
  if (view.selected === chunk.id) node.classList.add("selected");
  node.setAttribute("aria-label", `${chunk.text}：${chunk.role === "M" ? labelText(chunk) : ROLE_NAME[chunk.role]}`);
  node.append(makeLabel(chunk));

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
  const btn = el("button", `speak ${extra}`);
  btn.append(icon("volume"), el("span", "speak-label", label));
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
  // 分詞構句：還原成完整的句子，列出精簡的步驟
  if (chunk.restore) {
    const r = el("div", "restore");
    r.append(el("div", "restore-h", "還原成完整的句子"), el("div", "restore-s", chunk.restore.clause));
    const ol = el("ol", "restore-steps");
    chunk.restore.steps.forEach((t) => ol.append(el("li", null, t)));
    r.append(ol);
    box.append(r);
  }
  // 單字列表先不顯示（使用者決定 2026-10-01），之後改成點單字查詢
  return box;
}

// ---------- 查單字：片段裡重要單字的音標和中文意思（ECDICT） ----------
const lookupCache = new Map();
function fetchWords(text) {
  if (!lookupCache.has(text)) {
    lookupCache.set(text, fetch("/api/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.slice(0, 300) }),
    }).then((r) => (r.ok ? r.json() : { words: [] })).then((d) => d.words).catch(() => []));
  }
  return lookupCache.get(text);
}

function wordList(text) {
  const wrap = el("div", "lookup");
  fetchWords(text).then((words) => {
    if (!words.length) return;
    wrap.append(el("span", "lookup-title", "📖 單字"));
    const ul = el("ul", "lookup-list");
    for (const w of words) {
      const li = el("li");
      li.append(el("b", "lookup-word", w.word));
      if (w.form_only) li.append(el("span", "lookup-base", `（${w.base} 的變化形）`));
      if (w.phonetic) li.append(el("span", "lookup-ph", `/${w.phonetic}/`));
      li.append(el("span", "lookup-mean", w.meaning));
      if (w.base_meaning) li.append(el("span", "lookup-also", `也是 ${w.base} 的變化形：${w.base_meaning}`));
      ul.append(li);
    }
    wrap.append(ul);
    wrap.append(el("span", "lookup-src", "字典：ECDICT"));
  });
  return wrap;
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
  head.append(el("span", "card-title", card.title));
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
    throw new Error(typeof body.detail === "string" ? body.detail : "送不出去，網路好像打結了，等一下再試。");
  }
}

function feedbackForm(sIdx) {
  const sentence = sentences[sIdx];
  const view = views[sIdx];
  const form = el("form", "feedback");
  form.append(el("p", "fb-title", "偵探貓哪裡看走眼了？"));

  const text = el("textarea");
  text.rows = 2;
  text.maxLength = 1000;
  text.placeholder = "例如：in the garden 應該是副詞・表地點（句子和分析結果會自動附上）";
  text.setAttribute("aria-label", "哪裡分析錯了");
  const note = el("p", "fb-note", "請不要填寫姓名、電話等個人資料。");
  const status = el("p", "fb-status");
  const send = el("button", "primary", "回報錯誤");
  send.type = "submit";
  form.append(text, note, send, status);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!text.value.trim()) {
      status.textContent = "先告訴偵探貓錯在哪啦。";
      return;
    }
    send.disabled = true;
    try {
      await sendFeedback({ kind: "error", sentence: sentence.text, message: text.value.trim(), analysis: sentence });
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
// 「試試看」範例句：點一下就分析
for (const chip of document.querySelectorAll(".example-chip")) {
  chip.addEventListener("click", () => {
    input.value = chip.textContent;
    updateCounter();
    form.requestSubmit();
  });
}

const suggestForm = $("suggest-form");
// 回饋對話框：首頁下方的「寫下你的想法」和結果下方的「給我回饋」都會打開它
const feedbackDialog = $("feedback-dialog");
for (const btn of document.querySelectorAll("[data-open-feedback]")) {
  btn.addEventListener("click", () => {
    $("suggest-status").textContent = "";
    feedbackDialog.showModal();
    $("suggest-text").focus();
  });
}
feedbackDialog?.querySelector("[data-close-feedback]").addEventListener("click", () => feedbackDialog.close());
feedbackDialog?.addEventListener("click", (e) => {
  if (e.target === feedbackDialog) feedbackDialog.close(); // 點對話框外面也可以關掉
});

if (suggestForm) {
  suggestForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const box = $("suggest-text");
    const status = $("suggest-status");
    if (!box.value.trim()) {
      status.textContent = "空白的偵探貓看不懂啦，寫點什麼吧。";
      return;
    }
    try {
      await sendFeedback({ kind: "suggestion", message: box.value.trim() });
      box.value = "";
      status.textContent = "收到！偵探貓會認真看，說不定下一版就有了 🐾";
      setTimeout(() => feedbackDialog?.close(), 1800);
    } catch (err) {
      status.textContent = err.message;
    }
  });
}

// ---------- 拼字提醒：是不是打錯字？ ----------
function typoBanner(sentence) {
  const box = el("div", "banner typo");
  const parts = sentence.typos.map((t) => (t.suggestion ? `「${t.word}」是不是「${t.suggestion}」？` : `「${t.word}」好像不是英文單字，請確認拼字。`));
  box.append(icon("pencil"), el("span", null, `偵探貓發現可疑字跡：${parts.join("")}打錯字會讓偵探貓辦錯案，改正後再分析一次比較準。`));
  const fixes = sentence.typos.filter((t) => t.suggestion);
  if (fixes.length) {
    const btn = el("button", "typo-fix", fixes.length === 1 ? `改成 ${fixes[0].suggestion} 再分析` : "全部改正再分析");
    btn.type = "button";
    btn.addEventListener("click", () => {
      let text = input.value;
      for (const t of fixes) {
        const esc = t.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        text = text.replace(new RegExp(`\\b${esc}\\b`), t.suggestion);
      }
      input.value = text;
      updateCounter();
      form.requestSubmit();
    });
    box.append(btn);
  }
  return box;
}

// ---------- 一整句 ----------
// 片語卡放最上面；文法重點只列標題、一個一行，點了在那一行下面展開說明
function grammarSection(sIdx) {
  const sentence = sentences[sIdx];
  const view = views[sIdx];
  const refs = sentence.cards || [];
  if (!refs.length && !sentence.phrases?.length) return null;
  const sec = el("div", "gp-sec");
  if (sentence.phrases?.length) sec.append(phraseCard(sentence));
  if (refs.length) {
    const list = el("div", "gp-list");
    sec.append(el("p", "sec-title", "文法重點"), list);
    for (const ref of refs) {
      const item = el("div", "gp-item");
      list.append(item);
      fetchCard(ref.id).then((card) => {
        if (!card) {
          item.remove();
          return;
        }
        const open = view.openCards.has(ref.id);
        const chip = el("button", open ? "gp-chip on" : "gp-chip", card.title);
        chip.type = "button";
        chip.setAttribute("aria-expanded", String(open));
        chip.addEventListener("click", () => {
          open ? view.openCards.delete(ref.id) : view.openCards.add(ref.id);
          renderSentence(sIdx);
        });
        item.append(chip);
        if (open) item.append(cardNode(sIdx, ref, card));
      });
    }
  }
  return sec;
}

// 圖示＋文字的小按鈕（朗讀、回報錯誤）：手機上換短字，才能和句型公式排在同一列
function toolButton(name, long, short, onClick) {
  const btn = el("button", "tool-btn");
  btn.type = "button";
  btn.append(icon(name), el("span", "label-long", long), el("span", "label-short", short));
  btn.addEventListener("click", onClick);
  return btn;
}

function renderSentence(sIdx) {
  const sentence = sentences[sIdx];
  const view = views[sIdx];
  const box = view.node;
  box.replaceChildren();

  if (view.sample) {
    const tag = el("div", "sample-tag");
    tag.append(cat("idle"), el("span", null, "範例"));
    box.append(tag);
  }

  // 第一列：左邊是編號、句型公式（可以換行），右邊固定是朗讀和回報
  const head = el("div", "s-head");
  const meta = el("div", "s-meta");
  head.append(meta);
  if (sentences.length > 1) meta.append(el("span", "s-num", String(sIdx + 1)));
  if (sentence.kind === "compound") meta.append(el("span", "tag", "對等句"));
  if (sentence.clauses.length) {
    // 句型標籤可以點，打開五大句型介紹的對應段落
    // 複句的公式（句型二：… & 句型三：…）只在 & 的地方換行，不從一段公式中間斷開
    const link = el("a", "pattern");
    sentence.header.split(/\s*&\s*/).forEach((part, i) => {
      if (i) link.append(" & ");
      link.append(el("span", "pf", part));
    });
    link.href = `/patterns#p${sentence.clauses[0].pattern}`;  // 在同一頁打開（使用者要求）；按上一頁回來會自動重新分析
    link.title = "看這個句型的說明";
    meta.append(link);
  }
  // 動詞句型字典檢查不通過：提醒這句可能分析錯了（點開看原因）
  const doubts = sentence.clauses.map((c) => c.doubt).filter(Boolean);
  if (doubts.length) {
    const flag = el("button", "doubt");
    flag.append(icon("alert"), "偵探貓對這句沒把握");
    flag.type = "button";
    flag.setAttribute("aria-expanded", String(Boolean(view.doubtOpen)));
    flag.addEventListener("click", () => {
      view.doubtOpen = !view.doubtOpen;
      renderSentence(sIdx);
    });
    meta.append(flag);
  }
  const tools = el("span", "s-tools");
  if (window.Speech?.available && sentence.status !== "failed") {
    tools.append(toolButton("volume", "朗讀", "朗讀", (e) => {
      e.stopPropagation();
      window.Speech.speak(sentence.text);
    }));
  }
  if (!view.sample) {
    const sent = view.feedback === "sent";
    const report = toolButton(sent ? "check" : "flag", sent ? "收到，偵探貓去罰站了" : "回報錯誤", sent ? "收到" : "回報", () => {
      view.feedback = view.feedback === "open" ? null : "open";
      renderSentence(sIdx);
    });
    report.disabled = sent;
    if (view.feedback === "open") report.classList.add("on");
    tools.append(report);
  }
  head.append(tools);
  box.append(head);
  if (doubts.length && view.doubtOpen) {
    box.append(el("div", "banner doubt-note", `${doubts.join(" ")}如果你知道正確答案，按「回報錯誤」教教偵探貓。`));
  }

  if (sentence.status === "failed" && sentences.length > 1) box.append(el("p", "failed-text", sentence.text));
  if (sentence.typos?.length) {
    box.append(typoBanner(sentence));  // 打錯字常常讓整句看錯，先提醒改字，不顯示「這句比較複雜」
  } else if (sentence.status !== "ok" && sentence.message) {
    box.append(el("div", `banner${sentence.status === "failed" ? " fail" : ""}`, sentence.message));
  }
  if (sentence.status !== "failed") {
    box.append(chunkRow(sIdx));
    scheduleOverlapFix();
  }

  const explain = explainBox(sentence, view);
  if (explain) box.append(explain);
  if (view.feedback === "open") box.append(feedbackForm(sIdx));

  const zh = el("p", "zh");
  zh.dataset.translation = String(sIdx);
  if (sentence.translation) {
    zh.textContent = sentence.translation;
    zh.append(el("span", "mt", "機器翻譯"));
  } else if (sentence.translationStatus) {
    zh.append(el("span", "zh-status", sentence.translationStatus));
  }
  box.append(zh);

  const grammar = grammarSection(sIdx);
  if (grammar) box.append(grammar);
}

function render(data, { sample = false } = {}) {
  sentences = data.sentences;
  result.replaceChildren();
  result.dataset.sample = sample ? "1" : "";
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
    const node = el("article", sample ? "sentence sample" : "sentence");
    node.id = `s${i + 1}`;
    result.append(node);
    return { node, sample, selected: null, expanded: new Set(), openCards: new Set(), feedback: null };
  });
  sentences.forEach((_, i) => renderSentence(i));
  toolbar.hidden = sample;
  $("result-actions").hidden = sample;
  document.dispatchEvent(new CustomEvent("analysis-rendered", { detail: { sentences } }));
}

// 結果的開頭不在畫面裡時（手機上常見），捲到結果卡的頂端
function bringIntoView(node) {
  const top = node.getBoundingClientRect().top;
  if (top >= 0 && top < window.innerHeight * 0.6) return;
  const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  node.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
}

// ---------- 輸入 ----------
function showError(message) {
  errorBox.replaceChildren(cat("oops"), el("span", null, message));
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
  if (!text) return showError("你什麼都沒貼，偵探貓的放大鏡對著空氣很尷尬。貼一句英文進來吧。");
  if (text.length > MAX_CHARS) return showError(`這篇長到偵探貓的放大鏡起霧了，請控制在 ${MAX_CHARS} 個字元以內。`);
  try { sessionStorage.setItem("last", text); } catch { /* 無痕模式等情況，不影響使用 */ }

  submit.disabled = true;
  submit.textContent = "分析中…";
  const loading = el("div", "loading");
  const loadingText = el("p", null, "偵探貓辦案分析中…");
  loading.append(cat("work"), loadingText);
  result.dataset.sample = "";
  result.replaceChildren(loading);
  // 等超過 3 秒才補一句說明，平常很快就好的時候不用多看一行字
  const slowTimer = setTimeout(() => {
    loadingText.textContent = "偵探貓辦案分析中…第一次辦案要先把工具準備好，會比較久，等偵探貓一下。";
  }, 3000);
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
      showError(typeof body.detail === "string" ? body.detail : "偵探貓卡關了，等一下再試一次。");
      return;
    }
    render(await response.json());
    addHistory(text);
    bringIntoView(result);
  } catch {
    result.replaceChildren();
    showError("偵探貓聯絡不上網站，檢查一下網路，再按一次「分析」。");
  } finally {
    clearTimeout(slowTimer);
    submit.disabled = false;
    submit.textContent = "分析";
  }
});

// ---------- 分享（F6） ----------
// 分享某一句的分析時，句子放在網址的 # 後面：這部分不會送到伺服器（share() 在 share.js）
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
  fixLabelOverlap(); // 修飾語的說明印出來時也要錯開，不能疊在旁邊的標籤上
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
  const before = storageGet("history") || "[]";
  storageSet("history", "[]");
  renderHistory();
  // 一按就清掉太可惜：提示後面放「復原」，按錯可以拿回來
  showToast("已清除紀錄", {
    label: "復原",
    onClick: () => {
      storageSet("history", before);
      renderHistory();
    },
  });
});

// 測試版（免費主機、小型模型）才顯示提示；翻譯失敗時的說明也看這個記號（translate.js）
fetch("/api/site")
  .then((r) => (r.ok ? r.json() : {}))
  .then((site) => {
    if (!site.test_edition) return;
    document.documentElement.dataset.edition = "test";
    $("test-notice").hidden = false;
  })
  .catch(() => { /* 拿不到就當完整版 */ });

updateCounter();
renderHistory();
if (!location.hash.startsWith("#q=")) render(SAMPLE, { sample: true });
loadFromHash();

// 從五大句型頁按「上一頁」回來時，分析結果可能已經被瀏覽器清掉 → 自動重新分析上一次的句子
function restoreAfterBack() {
  const nav = performance.getEntriesByType("navigation")[0];
  if (!nav || nav.type !== "back_forward" || location.hash.startsWith("#q=") || (result.childElementCount && !result.dataset.sample)) return;
  let last = null;
  try { last = sessionStorage.getItem("last"); } catch { return; }
  if (!last) return;
  input.value = last;
  updateCounter();
  form.requestSubmit();
}
restoreAfterBack();
// 點去五大句型頁時做記號：那邊的「回到句子分析」就用上一頁，回來看得到剛才的分析
document.addEventListener("click", (e) => {
  if (e.target.closest?.('a[href^="/patterns"]')) {
    try { sessionStorage.setItem("fromAnalysis", "1"); } catch { /* 不影響使用 */ }
  }
});
