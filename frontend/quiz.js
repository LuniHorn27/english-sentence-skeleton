// 句型小遊戲（F2）
//   選玩法 → 一回合 10 題（上方有進度）→ 成績與答錯的題目複習
//   玩法一「句型判斷」：看句子，選出句型（五選一，可以按數字鍵 1～5）
//   玩法二「找骨架」：依公式順序，在句子裡點出主詞、動詞、受詞……每找對一個就上色
// 題目來自人工審核過的練習題（tests/practice/gold.yaml）；考試題保持封存，不拿來出題。

const ROUND = 10;
const GROUP = { S: "S", Vt: "V", Vi: "V", V: "V", aux: "V", O: "O", IO: "O", DO: "O", SC: "C", OC: "C" };
const CORE = new Set(["S", "Vt", "Vi", "V", "O", "IO", "DO", "SC", "OC"]);
const ROLE_NAME = {
  S: "主詞", Vt: "動詞", Vi: "動詞", V: "動詞", O: "受詞", IO: "間接受詞", DO: "直接受詞",
  SC: "主詞補語", OC: "受詞補語", M: "修飾語", aux: "助動詞", RS: "真主詞", RO: "真受詞",
};
// [內部代號, 顯示編號, 公式]，依賴世雄的編號排列
const PATTERNS = [
  [1, "句型一", "S + Vi"], [3, "句型二", "S + Vi + SC"], [2, "句型三", "S + Vt + O"],
  [5, "句型四", "S + Vt + O + OC"], [4, "句型五", "S + Vt + IO + DO"],
];
const MODES = {
  pattern: { icon: "🧩", name: "句型判斷", desc: "看一個句子，從五種句型裡選出正確的一個。" },
  skeleton: { icon: "🎯", name: "找骨架", desc: "照公式的順序，在句子裡點出主詞、動詞、受詞、補語。" },
};

const game = document.getElementById("game");
let state = null; // { mode, items, index, results: [{ item, ok, detail }] }

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, className, onClick) {
  const b = el("button", className, text);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}
function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { /* 瀏覽器不允許儲存時就不記錄最佳成績 */ }
  return null;
}

const patternInfo = (item) => PATTERNS.find(([n]) => n === item.pattern);
function patternLabel(item) {
  const [, name, formula] = patternInfo(item);
  if (!item.passive) return `${name}：${formula}`;
  const rest = { 4: " + DO", 5: " + OC" }[item.pattern] || "";
  return `${name}（被動語態）：S + be + p.p.${rest}`;
}
const textOf = (item, roles) => item.chunks.filter((c) => roles.includes(c.role)).map((c) => c.text).join(" ");

// 為什麼是這個句型（用句子裡的字說明）
function why(item) {
  const v = textOf(item, ["Vt", "Vi", "V"]);
  const s = textOf(item, ["S"]);
  if (item.passive) return `這句是被動語態：主詞 ${s} 是動作的承受者，看「改成被動之前」的句型。`;
  switch (item.pattern) {
    case 1: return `${v} 後面不需要受詞或補語，意思就完整了；後面的字都是修飾語。`;
    case 3: return `${v} 後面接主詞補語 ${textOf(item, ["SC"])}，說明主詞：${s} ＝ ${textOf(item, ["SC"])}。`;
    case 2: return `${v} 後面接受詞 ${textOf(item, ["O"])}，是動作的對象（${s} ≠ ${textOf(item, ["O"])}）。`;
    case 5: return `${v} 後面接受詞 ${textOf(item, ["O"])}，再接受詞補語 ${textOf(item, ["OC"])}：${textOf(item, ["O"])} ＝ ${textOf(item, ["OC"])}。`;
    case 4: return `${v} 後面接兩個受詞：${textOf(item, ["IO"])}（給誰）和 ${textOf(item, ["DO"])}（給什麼）。`;
    default: return "";
  }
}

// 骨架答案：和分析頁相同的樣式
function answerRow(item, revealAll = true) {
  const row = el("div", "row");
  for (const c of item.chunks) {
    const core = c.role !== "M";
    const ck = el("span", `ck ${core ? `${c.role === "aux" || c.role === "RS" || c.role === "RO" ? "soft" : "core"} r-${GROUP[c.role] || "S"}` : "m"}`);
    const label = core ? (c.role === "aux" ? "aux." : c.role === "V" ? "Vi" : c.role) : c.function || "修飾語";
    ck.append(el("span", "lb", revealAll ? label : ""), el("span", "tx", c.text));
    row.append(ck);
  }
  return row;
}

// ---------- 開始畫面 ----------
function renderStart(message) {
  state = null;
  game.replaceChildren();
  if (message) game.append(el("p", "error", message));
  game.append(el("h2", "game-title", "選一種玩法"));
  const cards = el("div", "mode-cards");
  for (const [key, m] of Object.entries(MODES)) {
    const card = button("", "mode-card", () => start(key));
    const best = store(`quiz-best-${key}`);
    card.append(el("span", "mode-icon", m.icon), el("span", "mode-name", m.name), el("span", "mode-desc", m.desc));
    if (best) card.append(el("span", "mode-best", `最佳成績：${best}／${ROUND}`));
    cards.append(card);
  }
  game.append(cards);
}

async function start(mode) {
  game.replaceChildren(el("p", "loading", "偵探貓正在出題…"));
  try {
    const response = await fetch(`/api/quiz?count=${ROUND}`);
    if (!response.ok) throw new Error();
    const { items } = await response.json();
    state = { mode, items, index: 0, results: [] };
    renderQuestion();
  } catch {
    renderStart("題目被偵探貓打翻了，等一下再試。");
  }
}

// ---------- 題目共用的上方資訊列 ----------
function header() {
  const { mode, items, index, results } = state;
  const bar = el("div", "game-head");
  const info = el("div", "game-info");
  info.append(el("span", "game-mode", `${MODES[mode].icon} ${MODES[mode].name}`));
  info.append(el("span", "game-count", `第 ${index + 1}／${items.length} 題`));
  info.append(el("span", "game-score", `✓ ${results.filter((r) => r.ok).length}`));
  info.append(button("結束", "link-btn game-quit", () => askQuit(bar)));
  const progress = el("div", "progress");
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-valuenow", String(index));
  progress.setAttribute("aria-valuemax", String(items.length));
  const fill = el("div", "progress-fill");
  fill.style.width = `${(index / items.length) * 100}%`;
  progress.append(fill);
  bar.append(info, progress);
  return bar;
}

// 還沒答題就直接結束；答過題目先問一聲，免得誤按把這回合的進度弄丟
function askQuit(bar) {
  const done = state.results.length;
  if (done === 0) return renderStart();
  if (bar.querySelector(".quit-confirm")) return;
  const box = el("div", "quit-confirm");
  box.setAttribute("role", "alert");
  box.append(el("span", "quit-text", `要結束這回合嗎？已經答了 ${done} 題，結束後不會記錄成績。`));
  const keep = button("繼續作答", "", () => box.remove());
  box.append(button("結束這回合", "danger", () => renderStart()), keep);
  bar.insertBefore(box, bar.querySelector(".progress"));
  keep.focus();
}

function renderQuestion() {
  game.replaceChildren(header());
  const card = el("div", "q-card");
  game.append(card);
  (state.mode === "pattern" ? askPattern : askSkeleton)(state.items[state.index], card);
}

// 答完一題：顯示回饋和「下一題」
function feedback(card, item, ok, verdict) {
  state.results.push({ item, ok });
  game.querySelector(".game-score").textContent = `✓ ${state.results.filter((r) => r.ok).length}`;
  const box = el("div", `q-feedback ${ok ? "good" : "bad"}`);
  box.append(el("p", "q-verdict", verdict));
  box.append(el("p", "q-answer", patternLabel(item)));
  box.append(el("p", "q-why", why(item)));
  if (state.mode === "pattern") box.append(answerRow(item));
  const bar = el("div", "q-bar");
  const link = el("a", null, "看這個句型的說明");
  link.href = `/patterns#p${item.pattern}`;
  const last = state.index + 1 >= state.items.length;
  const next = button(last ? "看成績" : "下一題 →", "primary q-next", () => {
    state.index += 1;
    last ? renderEnd() : renderQuestion();
  });
  bar.append(link, next);
  box.append(bar);
  card.append(box);
  next.focus({ preventScroll: true });
  box.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// ---------- 玩法一：句型判斷 ----------
function askPattern(item, card) {
  card.append(el("p", "q-prompt", "這句是哪一種句型？"));
  card.append(el("p", "q-sentence", item.sentence));
  if (item.zh) card.append(el("p", "q-zh", item.zh));
  const list = el("div", "q-options");
  PATTERNS.forEach(([n, name, formula], i) => {
    const b = button("", "q-option", () => choose(n, b));
    b.dataset.n = String(n);
    b.append(el("span", "q-key", String(i + 1)), el("span", "q-name", name), el("span", "q-formula", formula));
    list.append(b);
  });
  card.append(list);

  function choose(n, picked) {
    list.querySelectorAll("button").forEach((x) => { x.disabled = true; });
    const ok = n === item.pattern;
    list.querySelector(`[data-n="${item.pattern}"]`).classList.add("is-right");
    if (!ok) picked.classList.add("is-wrong");
    feedback(card, item, ok, ok ? "破案！" : `欸不是，這句不是${PATTERNS.find(([x]) => x === n).slice(1).join(" ")}。`);
  }
}

// ---------- 玩法二：找骨架 ----------
function askSkeleton(item, card) {
  // 要找的步驟：主詞 → 動詞 → 動詞後面的成分（照句子裡的順序）
  const cores = item.chunks.map((c, i) => ({ c, i })).filter(({ c }) => CORE.has(c.role));
  const rank = (r) => (r === "S" ? 0 : ["Vt", "Vi", "V"].includes(r) ? 1 : 2);
  const steps = cores.sort((a, b) => rank(a.c.role) - rank(b.c.role) || a.i - b.i);
  let step = 0;
  let mistakes = 0;

  card.append(el("p", "q-prompt", "照順序找出這句的骨架"));
  const chips = el("div", "step-chips");
  // 還沒做到的步驟顯示「？」，免得一開始就洩漏句型
  steps.forEach(() => chips.append(el("span", "step-chip", "？")));
  card.append(chips);
  const ask = el("p", "q-ask");
  card.append(ask);
  const tiles = el("div", "q-tiles");
  const tileNodes = item.chunks.map((c, i) => {
    const t = button("", `q-tile${c.implicit ? " implicit" : ""}`, () => pick(i, t));
    t.append(el("span", "lb", ""), el("span", "tx", c.text));
    tiles.append(t);
    return t;
  });
  card.append(tiles);
  if (item.zh) card.append(el("p", "q-zh", item.zh));
  const hint = el("p", "q-tip");
  hint.hidden = true;
  card.append(hint);
  if (item.chunks.some((c) => c.implicit)) card.append(el("p", "q-hint", "括號裡的 (You) 是祈使句省略的主詞。"));
  updateAsk();

  function updateAsk() {
    chips.querySelectorAll(".step-chip").forEach((x, i) => {
      const role = steps[i].c.role;
      x.className = `step-chip${i <= step ? ` r-${GROUP[role]}` : ""}${i < step ? " done" : i === step ? " now" : ""}`;
      x.textContent = i <= step ? role : "？";
    });
    if (step < steps.length) {
      const role = steps[step].c.role;
      ask.replaceChildren(`第 ${step + 1} 步：點出`, el("b", `ask-role r-${GROUP[role]}`, `${ROLE_NAME[role]}（${role === "V" ? "Vi" : role}）`));
    }
  }

  function pick(i, tile) {
    if (step >= steps.length || tile.classList.contains("found")) return;
    const want = steps[step].c.role;
    const got = item.chunks[i].role;
    const sameVerb = ["Vt", "Vi", "V"].includes(want) && ["Vt", "Vi", "V"].includes(got);
    if (got === want || sameVerb) {
      tile.classList.add("found", `r-${GROUP[got]}`);
      tile.querySelector(".lb").textContent = got;
      tile.disabled = true;
      hint.hidden = true;
      step += 1;
      updateAsk();
      if (step === steps.length) {
        ask.replaceChildren("骨架完成：", el("b", null, patternLabel(item)));
        tileNodes.forEach((t, j) => {
          const c = item.chunks[j];
          t.disabled = true;
          if (!t.classList.contains("found")) {
            t.classList.add("rest");
            t.querySelector(".lb").textContent = c.role === "M" ? "修飾" : c.role === "aux" ? "aux." : c.role === "V" ? "Vi" : c.role;
          }
        });
        const ok = mistakes === 0;
        feedback(card, item, ok, ok ? "一次全對，你比偵探貓還會辦案。" : `破案了，中間繞了 ${mistakes} 次遠路。`);
      }
    } else {
      mistakes += 1;
      tile.classList.remove("shake");
      void tile.offsetWidth; // 重新觸發動畫
      tile.classList.add("shake");
      hint.hidden = false;
      hint.textContent = `「${item.chunks[i].text}」是${ROLE_NAME[got] || "其他成分"}，不是${ROLE_NAME[want]}。線索不對，再找找。`;
    }
  }
}

// ---------- 成績 ----------
function renderEnd() {
  const { mode, items, results } = state;
  const score = results.filter((r) => r.ok).length;
  const best = Number(store(`quiz-best-${mode}`) || 0);
  if (score > best) store(`quiz-best-${mode}`, String(score));

  game.replaceChildren();
  const card = el("div", "q-card end-card");
  const stars = score >= 9 ? "⭐⭐⭐" : score >= 7 ? "⭐⭐" : score >= 5 ? "⭐" : "";
  card.append(el("p", "end-stars", stars || "💪"));
  card.append(el("p", "end-score", `${score}／${items.length}`));
  const words = score === items.length ? "全部答對，偵探貓的飯碗不保了。" : score >= 7 ? "不錯喔，下面幾題是漏網之魚，抓回來看看。" : "沒關係，偵探貓剛入行也常看走眼，多玩幾回合就越看越清楚。";
  card.append(el("p", "end-words", words));
  if (score > best && best > 0) card.append(el("p", "end-best", "🎉 新紀錄！偵探貓幫你記下來了。"));

  const bar = el("div", "end-bar");
  bar.append(button("再玩一回合", "primary", () => start(mode)), button("換一種玩法", null, () => renderStart()));
  card.append(bar);
  game.append(card);

  const missed = results.filter((r) => !r.ok);
  if (missed.length) {
    const review = el("section", "review");
    review.append(el("h2", "game-title", `複習答錯的 ${missed.length} 題`));
    for (const { item } of missed) {
      const box = el("div", "review-item");
      box.append(el("p", "q-answer", patternLabel(item)), answerRow(item));
      if (item.zh) box.append(el("p", "q-zh", item.zh));
      box.append(el("p", "q-why", why(item)));
      review.append(box);
    }
    game.append(review);
  }
}

// 鍵盤：1～5 選句型，Enter 下一題
document.addEventListener("keydown", (e) => {
  if (!state || e.altKey || e.ctrlKey || e.metaKey) return;
  if (state.mode === "pattern" && /^[1-5]$/.test(e.key)) {
    const b = game.querySelectorAll(".q-option")[Number(e.key) - 1];
    if (b && !b.disabled) b.click();
  }
});

renderStart();
