// 五大句型介紹頁（2-4）。例句用和分析畫面相同的樣式呈現。

const GROUP = { S: "S", Vt: "V", Vi: "V", V: "V", O: "O", IO: "O", DO: "O", SC: "C", OC: "C" };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// 例句：[[文字, 角色], …]，角色 M 表示修飾語
function sentenceRow(parts) {
  const row = el("div", "row");
  for (const [text, role, fn] of parts) {
    const ck = el("span", `ck ${role === "M" ? "m" : `core r-${GROUP[role]}`}`);
    ck.append(el("span", "lb", role === "M" ? fn || "修飾語" : role), el("span", "tx", text));
    row.append(ck);
  }
  return row;
}

function callout(kind, name, icon, text, examples) {
  const box = el("div", `callout ${kind}`);
  box.append(el("span", "icon", icon));
  const body = el("div");
  body.append(el("span", "c-name", name), el("span", "c-text", text));
  if (examples) {
    const ul = el("ul", "examples");
    for (const [mark, en] of examples) {
      const li = el("li");
      li.append(el("span", mark === "ok" ? "mark-ok" : "mark-no", mark === "ok" ? "✓ " : "✗ "), el("span", "en", en));
      ul.append(li);
    }
    body.append(ul);
  }
  box.append(body);
  return box;
}

const LABELS = [
  ["S", "主詞", "做動作的人事物，或被描述的對象"],
  ["Vi", "不及物動詞", "後面不需要受詞"],
  ["Vt", "及物動詞", "後面需要受詞"],
  ["V", "連綴動詞", "像等號，後面接補語（be、look、become…）"],
  ["O", "受詞", "動作的對象"],
  ["IO", "間接受詞", "句型四：給「誰」"],
  ["DO", "直接受詞", "句型四：給「什麼」"],
  ["SC", "主詞補語", "說明主詞：主詞 ＝ 補語"],
  ["OC", "受詞補語", "說明受詞：受詞 ＝ 補語"],
];

const PATTERNS = [
  {
    n: 1, name: "句型一", formula: "S + Vi",
    idea: "主詞做了一個動作，這個動作不需要對象，句子就完整了。",
    test: "動詞後面沒有受詞也沒有補語；後面出現的都是修飾語（時間、地點、方式）。",
    examples: [
      [["Birds", "S"], ["fly", "Vi"]],
      [["The baby", "S"], ["is sleeping", "Vi"], ["in her room", "M", "副詞・表地點"]],
      [["She", "S"], ["smiled", "Vi"], ["happily", "M", "副詞・表方式"]],
    ],
    warn: ["不及物動詞後面不能直接接名詞，要先加介系詞。", [["no", "He arrived the station."], ["ok", "He arrived at the station."]]],
  },
  {
    n: 2, name: "句型二", formula: "S + Vt + O",
    idea: "主詞對某個對象做了動作，這個對象就是受詞。",
    test: "問「動詞 ＋ 什麼？」有答案，而且答案和主詞不是同一個東西。",
    examples: [
      [["I", "S"], ["like", "Vt"], ["you", "O"]],
      [["She", "S"], ["reads", "Vt"], ["a book", "O"], ["every night", "M", "副詞・表時間"]],
      [["They", "S"], ["enjoy", "Vt"], ["playing basketball", "O"]],
    ],
    warn: ["及物動詞一定要有受詞，也不要多加介系詞。", [["no", "We discussed about the problem."], ["ok", "We discussed the problem."]]],
  },
  {
    n: 3, name: "句型三", formula: "S + V + SC",
    idea: "動詞像等號，把主詞和後面的補語連起來，說明主詞「是什麼」或「怎麼樣」。",
    test: "等號測試：主詞 ＝ 補語 說得通。常見的動詞：be、look、sound、smell、taste、feel、become、get、turn、stay。",
    examples: [
      [["She", "S"], ["is", "V"], ["a nurse", "SC"]],
      [["The soup", "S"], ["smells", "V"], ["good", "SC"]],
      [["He", "S"], ["became", "V"], ["a doctor", "SC"]],
    ],
    warn: ["補語用形容詞，不用副詞。", [["no", "The soup smells well."], ["ok", "The soup smells good."]]],
  },
  {
    n: 4, name: "句型四", formula: "S + Vt + IO + DO",
    idea: "主詞把某樣東西（DO）給了某個人（IO）。動詞後面有兩個受詞。",
    test: "改寫測試：可以改成「DO ＋ to／for ＋ IO」。常見的動詞：give、show、send、tell、buy、make。",
    examples: [
      [["The teacher", "S"], ["showed", "Vt"], ["us", "IO"], ["a picture", "DO"]],
      [["My mom", "S"], ["bought", "Vt"], ["me", "IO"], ["a new bike", "DO"]],
    ],
    warn: ["改寫成一個受詞時，介系詞不能省略。", [["no", "He gave a book me."], ["ok", "He gave a book to me."]]],
  },
  {
    n: 5, name: "句型五", formula: "S + Vt + O + OC",
    idea: "主詞讓受詞變成某種狀態，或把受詞叫做什麼。受詞後面的補語用來說明受詞。",
    test: "等號測試：受詞 ＝ 補語 說得通。常見的動詞：make、keep、find、call、name、elect、let、see。",
    examples: [
      [["The news", "S"], ["made", "Vt"], ["her", "O"], ["sad", "OC"]],
      [["We", "S"], ["named", "Vt"], ["our dog", "O"], ["Lucky", "OC"]],
      [["Please", "M", "副詞・表語氣"], ["keep", "Vt"], ["the door", "O"], ["open", "OC"]],
    ],
    warn: ["使役動詞 make、let 後面接原形動詞，不加 to。", [["no", "The teacher made us to clean the room."], ["ok", "The teacher made us clean the room."]]],
  },
];

// 標籤對照
const labels = document.getElementById("labels");
for (const [tag, name, desc] of LABELS) {
  const row = el("div", "label-row");
  const ck = el("span", `ck core r-${GROUP[tag]}`);
  ck.append(el("span", "lb", tag));
  row.append(ck, el("span", "label-name", name), el("span", "label-desc", desc));
  labels.append(row);
}

// 五個句型
const wrap = document.getElementById("patterns");
for (const p of PATTERNS) {
  const sec = el("section", "intro pattern-sec");
  sec.id = `p${p.n}`;
  const h = el("h2");
  h.append(el("span", "pattern", `${p.name}：${p.formula}`));
  sec.append(h, el("p", null, p.idea));
  sec.append(callout("c-formula", "公式", "ƒ", p.formula));
  sec.append(el("h4", null, "怎麼判斷"), el("p", "muted", p.test));
  sec.append(el("h4", null, "例句"));
  p.examples.forEach((ex) => sec.append(sentenceRow(ex)));
  sec.append(callout("c-warn", "常見錯誤", "⚠", p.warn[0], p.warn[1]));
  wrap.append(sec);
}

// 句型四 vs 五
const cmp = document.getElementById("compare-examples");
cmp.append(el("h4", null, "句型四：她做了一個蛋糕給他"));
cmp.append(sentenceRow([["She", "S"], ["made", "Vt"], ["him", "IO"], ["a cake", "DO"]]));
cmp.append(el("h4", null, "句型五：她讓他很開心"));
cmp.append(sentenceRow([["She", "S"], ["made", "Vt"], ["him", "O"], ["happy", "OC"]]));

// 從分析頁點過來時，捲到對應的句型
if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
