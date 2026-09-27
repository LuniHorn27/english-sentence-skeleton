// 句型小遊戲（F2）：兩種題型輪流出現
//   1. 這句是哪一種句型？（五選一）
//   2. 點出句子裡的主詞／動詞／受詞／補語

const GROUP = { S: "S", Vt: "V", Vi: "V", V: "V", aux: "V", O: "O", IO: "O", DO: "O", SC: "C", OC: "C" };
// [內部代號, 顯示文字]，依賴世雄的編號排列
const PATTERNS = [
  [1, "句型一：S + Vi"], [3, "句型二：S + V + SC"], [2, "句型三：S + Vt + O"],
  [5, "句型四：S + Vt + O + OC"], [4, "句型五：S + Vt + IO + DO"],
];
const TARGETS = {
  S: ["主詞（S）", (r) => r === "S"],
  V: ["主要動詞（Vt／Vi／V）", (r) => r === "Vt" || r === "Vi" || r === "V"],
  O: ["受詞（O）", (r) => r === "O"],
  IO: ["間接受詞（IO）", (r) => r === "IO"],
  DO: ["直接受詞（DO）", (r) => r === "DO"],
  SC: ["主詞補語（SC）", (r) => r === "SC"],
  OC: ["受詞補語（OC）", (r) => r === "OC"],
};

const quiz = document.getElementById("quiz");
const scoreBox = document.getElementById("score");
let right = 0;
let total = 0;
let round = 0;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function updateScore() {
  scoreBox.textContent = `答對 ${right} 題／共 ${total} 題`;
}

// 標出答案的骨架
function answerRow(item) {
  const row = el("div", "row");
  for (const c of item.chunks) {
    const core = c.role !== "M";
    const ck = el("span", `ck ${core ? `${c.role === "aux" ? "soft" : "core"} r-${GROUP[c.role]}` : "m"}`);
    ck.append(el("span", "lb", core ? (c.role === "aux" ? "aux." : c.role) : c.function), el("span", "tx", c.text));
    row.append(ck);
  }
  return row;
}

function patternLabel(item) {
  const label = PATTERNS.find(([n]) => n === item.pattern)[1];
  return item.passive ? label.replace("：", "（被動語態）：") : label;
}

function finish(item, ok, message) {
  total += 1;
  if (ok) right += 1;
  updateScore();
  const box = el("div", `quiz-result ${ok ? "good" : "bad"}`);
  box.append(el("p", "quiz-verdict", ok ? "答對了！" : "再想想看"));
  if (message) box.append(el("p", null, message));
  box.append(el("p", "quiz-sub", `這句是 ${patternLabel(item)}`));
  box.append(answerRow(item));
  const link = el("a", null, "看這個句型的說明");
  link.href = `/patterns#p${item.pattern}`;
  link.target = "_blank";
  link.rel = "noopener";
  const next = el("button", "primary", "下一題");
  next.type = "button";
  next.addEventListener("click", load);
  const bar = el("div", "quiz-bar");
  bar.append(link, next);
  box.append(bar);
  quiz.append(box);
  next.focus();
}

function askPattern(item) {
  quiz.append(el("p", "quiz-q", "這句是哪一種句型？"));
  quiz.append(el("p", "quiz-sentence", item.sentence));
  if (item.passive) quiz.append(el("p", "quiz-sub", "提示：這句是被動語態，請選「改成被動之前」的句型。"));
  const opts = el("div", "quiz-options");
  for (const [n, label] of PATTERNS) {
    const b = el("button", null, label);
    b.type = "button";
    b.addEventListener("click", () => {
      opts.querySelectorAll("button").forEach((x) => { x.disabled = true; });
      b.classList.add(n === item.pattern ? "pick-good" : "pick-bad");
      finish(item, n === item.pattern, n === item.pattern ? "" : `你選了${label.split("：")[0]}。`);
    });
    opts.append(b);
  }
  quiz.append(opts);
}

function askRole(item) {
  const present = new Set(item.chunks.map((c) => (["Vt", "Vi", "V"].includes(c.role) ? "V" : c.role)));
  const choices = Object.keys(TARGETS).filter((k) => present.has(k));
  const key = choices[Math.floor(Math.random() * choices.length)];
  const [name, match] = TARGETS[key];
  quiz.append(el("p", "quiz-q", `點出這句的${name}`));
  const row = el("div", "quiz-options chunks-pick");
  for (const c of item.chunks) {
    const b = el("button", null, c.text);
    b.type = "button";
    b.addEventListener("click", () => {
      row.querySelectorAll("button").forEach((x) => { x.disabled = true; });
      const ok = match(c.role);
      b.classList.add(ok ? "pick-good" : "pick-bad");
      const answer = item.chunks.filter((x) => match(x.role)).map((x) => x.text).join("、");
      finish(item, ok, ok ? "" : `正確答案是「${answer}」。`);
    });
    row.append(b);
  }
  quiz.append(row);
}

async function load() {
  quiz.replaceChildren(el("p", "loading", "題目準備中…"));
  try {
    const item = await (await fetch("/api/quiz")).json();
    quiz.replaceChildren();
    round += 1;
    (round % 2 ? askPattern : askRole)(item);
  } catch {
    quiz.replaceChildren(el("p", "error", "題目載入失敗，請重新整理頁面。"));
  }
}

load();
