// 五大句型介紹頁：參考文法書的教法（先講成分、再講動詞分類，最後逐一介紹句型）。
// 說明和例句都是自己寫的；例句的標法和分析程式的結果一致（改例句時請先用分析頁確認）。

const GROUP = { S: "S", Vt: "V", Vi: "V", V: "V", O: "O", IO: "O", DO: "O", SC: "C", OC: "C" };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// 例句：{ parts: [[文字, 角色, 修飾語功能?], …], zh: 中文 }
function example(ex) {
  const box = el("div", "ex");
  const row = el("div", "row");
  for (const [text, role, fn] of ex.parts) {
    const ck = el("span", `ck ${role === "M" ? "m" : `core r-${GROUP[role]}`}`);
    ck.append(el("span", "lb", role === "M" ? fn || "修飾語" : role), el("span", "tx", text));
    row.append(ck);
  }
  box.append(row);
  if (ex.zh) box.append(el("p", "ex-zh", ex.zh));
  return box;
}

function callout(kind, icon, name, text, examples) {
  const box = el("div", `callout ${kind}`);
  box.append(el("span", "icon", icon));
  const body = el("div");
  body.append(el("span", "c-name", name));
  if (text) body.append(el("span", "c-text", text));
  if (examples) {
    const ul = el("ul", "examples");
    for (const [mark, en] of examples) {
      const li = el("li");
      const cls = { ok: "mark-ok", no: "mark-no" }[mark];
      li.append(cls ? el("span", cls, mark === "ok" ? "✓ " : "✗ ") : "・", el("span", "en", en));
      ul.append(li);
    }
    body.append(ul);
  }
  box.append(body);
  return box;
}

// ---------- 一、句子的成分 ----------
const LABELS = [
  ["S", "主詞", "句子在說「誰」或「什麼」"],
  ["Vi", "不及物動詞", "後面不需要受詞，意思就完整"],
  ["Vt", "及物動詞", "後面一定要有受詞"],
  ["V", "動詞", "後面要接補語，意思才完整（be、seem、become…）"],
  ["O", "受詞", "動作的對象，接在及物動詞後面"],
  ["IO", "間接受詞", "接受東西的人（給「誰」）"],
  ["DO", "直接受詞", "被給的東西（給「什麼」）"],
  ["SC", "主詞補語", "補充說明主詞的身分或狀態"],
  ["OC", "受詞補語", "補充說明受詞的身分或狀態"],
  ["M", "修飾語", "補充時間、地點、方式等，不屬於骨架"],
];

const labels = document.getElementById("labels");
for (const [tag, name, desc] of LABELS) {
  const row = el("div", "label-row");
  const ck = el("span", tag === "M" ? "ck m" : `ck core r-${GROUP[tag]}`);
  ck.append(el("span", "lb", tag === "M" ? "修飾" : tag));
  row.append(ck, el("span", "label-name", name), el("span", "label-desc", desc));
  labels.append(row);
}

// ---------- 二、動詞決定句型 ----------
const VERB_TYPES = [
  ["完全不及物動詞", "不接受詞，也不接補語", "句型一：S + Vi", "Birds fly.", "p1"],
  ["不完全不及物動詞", "主詞補語", "句型二：S + V + SC", "She is a nurse.", "p3"],
  ["完全及物動詞", "一個受詞", "句型三：S + Vt + O", "I like music.", "p2"],
  ["不完全及物動詞", "受詞 ＋ 受詞補語", "句型四：S + Vt + O + OC", "They call him Tom.", "p5"],
  ["授與動詞", "間接受詞 ＋ 直接受詞", "句型五：S + Vt + IO + DO", "He gave me a book.", "p4"],
];

const verbRows = document.getElementById("verb-rows");
for (const [kind, needs, pattern, en, anchor] of VERB_TYPES) {
  const tr = el("tr");
  const link = el("a", null, pattern);
  link.href = `#${anchor}`;
  const td = el("td");
  td.append(link);
  tr.append(el("td", "vt-kind", kind), el("td", null, needs), td, el("td", "en", en));
  verbRows.append(tr);
}

// ---------- 三、五個句型 ----------
// n 是程式的內部代號（網址 #p 後面的數字）；顯示時用賴世雄的編號
const PATTERNS = [
  {
    n: 1, name: "句型一", formula: "S + Vi", verbKind: "主詞 ＋ 完全不及物動詞",
    idea: "動詞本身就把意思說完整了，後面不需要受詞，也不需要補語。句子後面常常接修飾語，說明時間、地點或方式。",
    formulaNote: "S + Vi（後面可以再接修飾語）",
    verbs: ["go、come、arrive、run、walk、swim", "sleep、cry、laugh、smile", "happen、rise、fall"],
    examples: [
      { parts: [["Birds", "S"], ["fly", "Vi"]], zh: "鳥會飛。" },
      { parts: [["The baby", "S"], ["is sleeping", "Vi"], ["in her room", "M", "副詞・表地點"]], zh: "寶寶在她的房間裡睡覺。" },
      { parts: [["The sun", "S"], ["rises", "Vi"], ["in the east", "M", "副詞・表地點"]], zh: "太陽從東方升起。" },
    ],
    warn: ["不及物動詞後面不能直接接名詞；要接對象時，先加介系詞。", [["no", "He arrived the station."], ["ok", "He arrived at the station."], ["no", "Please listen me."], ["ok", "Please listen to me."]]],
    info: ["補充：There is／There are", "There is a cat under the table. 這種句子表示「有、存在」，本網站把 be 動詞標成 Vi，真正的主詞是 be 後面的 a cat，There 是引導詞。"],
  },
  {
    n: 3, name: "句型二", formula: "S + V + SC", verbKind: "主詞 ＋ 不完全不及物動詞 ＋ 主詞補語",
    idea: "只寫到動詞，意思還不完整（She is…她是什麼？），必須再接主詞補語，說明主詞的身分、性質或狀態。補語可以是名詞，也可以是形容詞。",
    formulaNote: "S + V + SC（SC 是名詞或形容詞）",
    verbs: ["be 動詞：am、is、are、was、were", "感官動詞：look、sound、smell、taste、feel（看起來、聽起來、聞起來…）", "表示「變成、保持」：become、get、turn、grow、stay、keep、remain、seem"],
    examples: [
      { parts: [["She", "S"], ["is", "V"], ["a nurse", "SC"]], zh: "她是護理師。（補語是名詞）" },
      { parts: [["The soup", "S"], ["smells", "V"], ["good", "SC"]], zh: "這碗湯聞起來很香。（補語是形容詞）" },
      { parts: [["He", "S"], ["became", "V"], ["a doctor", "SC"]], zh: "他成為一名醫生。" },
      { parts: [["The leaves", "S"], ["turn", "V"], ["red", "SC"], ["in autumn", "M", "副詞・表時間"]], zh: "葉子在秋天變紅。" },
    ],
    tip: "判斷方法：主詞 ＝ 補語 說得通（She ＝ a nurse、The soup ＝ good）。",
    warn: ["補語要用形容詞，不能用副詞。", [["no", "She looks happily."], ["ok", "She looks happy."]]],
    info: ["補充：看後面接什麼", "He looks happy.（看起來很開心 → 句型二）\nHe looks at the picture.（看著照片：look 後面沒有補語，at the picture 是修飾語 → 句型一）"],
  },
  {
    n: 2, name: "句型三", formula: "S + Vt + O", verbKind: "主詞 ＋ 完全及物動詞 ＋ 受詞",
    idea: "動作一定有一個對象，這個對象就是受詞。受詞可以是名詞、代名詞，也可以是動名詞（V-ing）、不定詞（to V）或名詞子句。",
    formulaNote: "S + Vt + O",
    verbs: ["like、love、want、need、have、make、buy、read、eat、see", "enjoy、finish、practice（受詞用 V-ing）", "want、hope、decide、plan（受詞用 to V）"],
    examples: [
      { parts: [["I", "S"], ["like", "Vt"], ["music", "O"]], zh: "我喜歡音樂。" },
      { parts: [["She", "S"], ["reads", "Vt"], ["a book", "O"], ["every night", "M", "副詞・表時間"]], zh: "她每天晚上讀一本書。" },
      { parts: [["They", "S"], ["enjoy", "Vt"], ["playing basketball", "O"]], zh: "他們喜歡打籃球。（受詞是動名詞）" },
      { parts: [["I", "S"], ["want", "Vt"], ["to go home", "O"]], zh: "我想回家。（受詞是不定詞）" },
      { parts: [["I", "S"], ["think", "Vt"], ["that he is right", "O"]], zh: "我認為他是對的。（受詞是名詞子句）" },
    ],
    tip: "判斷方法：問「動詞 ＋ 什麼？」有答案，而且答案和主詞不相等（I ≠ music）。",
    warn: ["及物動詞一定要有受詞，也不要多加介系詞。", [["no", "We discussed about the problem."], ["ok", "We discussed the problem."], ["no", "She married with him."], ["ok", "She married him."]]],
    info: ["補充：被動語態", "受詞可以移到主詞的位置，變成被動語態：Mary wrote the letter. → The letter was written by Mary. 本網站會標成「句型三（被動語態）：S + be + p.p.」。"],
  },
  {
    n: 5, name: "句型四", formula: "S + Vt + O + OC", verbKind: "主詞 ＋ 不完全及物動詞 ＋ 受詞 ＋ 受詞補語",
    idea: "動詞後面有了受詞，意思還不完整，要再接受詞補語，說明受詞「是什麼」或「變得怎樣」。受詞補語可以是名詞、形容詞、原形動詞、不定詞或分詞。",
    formulaNote: "S + Vt + O + OC",
    verbs: ["使…成為：make、keep、leave、find", "稱呼、選為：call、name、elect", "使役動詞：make、let、have（＋ 原形動詞）", "要求、希望：ask、tell、want、allow（＋ to V）"],
    examples: [
      { parts: [["The news", "S"], ["made", "Vt"], ["her", "O"], ["sad", "OC"]], zh: "這個消息讓她很難過。（補語是形容詞）" },
      { parts: [["We", "S"], ["named", "Vt"], ["our dog", "O"], ["Lucky", "OC"]], zh: "我們把狗取名叫 Lucky。（補語是名詞）" },
      { parts: [["My mom", "S"], ["let", "Vt"], ["me", "O"], ["go out", "OC"]], zh: "媽媽讓我出去。（補語是原形動詞）" },
      { parts: [["The teacher", "S"], ["asked", "Vt"], ["us", "O"], ["to be quiet", "OC"]], zh: "老師要我們安靜。（補語是不定詞）" },
    ],
    tip: "判斷方法：受詞 ＝ 補語 說得通（her ＝ sad、our dog ＝ Lucky）。",
    warn: ["使役動詞 make、let、have 後面接原形動詞，不加 to。", [["no", "The teacher made us to clean the room."], ["ok", "The teacher made us clean the room."]]],
  },
  {
    n: 4, name: "句型五", formula: "S + Vt + IO + DO", verbKind: "主詞 ＋ 授與動詞 ＋ 間接受詞 ＋ 直接受詞",
    idea: "「授與」就是給予。動詞後面有兩個受詞：先接「人」（間接受詞，給誰），再接「東西」（直接受詞，給什麼）。",
    formulaNote: "S + Vt + IO（人）+ DO（東西）",
    verbs: ["give、send、show、tell、teach、lend、pass、bring", "buy、make、cook、get"],
    examples: [
      { parts: [["He", "S"], ["gave", "Vt"], ["me", "IO"], ["a book", "DO"]], zh: "他給我一本書。" },
      { parts: [["The teacher", "S"], ["showed", "Vt"], ["us", "IO"], ["a picture", "DO"]], zh: "老師給我們看一張照片。" },
      { parts: [["My mom", "S"], ["bought", "Vt"], ["me", "IO"], ["a new bike", "DO"]], zh: "媽媽買了一輛新腳踏車給我。" },
    ],
    rewrite: {
      text: "句型五可以把「東西」移到前面，「人」改用 to 或 for 帶出來。改寫之後 to me、for me 是修飾語，句子變成句型三（S + Vt + O）。",
      rows: [
        ["to", "東西送到對方手上：give、send、show、tell、teach、lend、pass", { parts: [["He", "S"], ["gave", "Vt"], ["a book", "O"], ["to me", "M", "副詞・表對象"]] }],
        ["for", "替對方做：buy、make、cook、get", { parts: [["My mom", "S"], ["bought", "Vt"], ["a new bike", "O"], ["for me", "M", "副詞・表目的"]] }],
      ],
    },
    tip: "判斷方法：IO ≠ DO（me ≠ a book），而且可以改寫成 to／for。",
    warn: ["改寫時介系詞不能省略。", [["no", "He gave a book me."], ["ok", "He gave a book to me."]]],
  },
];

// 依賴世雄的編號排列
const DISPLAY_ORDER = [1, 3, 2, 5, 4];
const wrap = document.getElementById("patterns");
DISPLAY_ORDER.forEach((n, i) => {
  const p = PATTERNS.find((x) => x.n === n);
  const sec = el("section", "intro pattern-sec");
  sec.id = `p${p.n}`;
  const h = el("h2");
  h.append(el("span", "sec-num", `${"三四五六七"[i]}、`), el("span", "pattern", `${p.name}：${p.formula}`));
  sec.append(h, el("p", "verb-kind", p.verbKind), el("p", null, p.idea));
  sec.append(callout("c-formula", "📍", "公式", p.formulaNote));

  sec.append(el("h4", null, "常見動詞"));
  const ul = el("ul", "plain");
  p.verbs.forEach((v) => ul.append(el("li", null, v)));
  sec.append(ul);

  sec.append(el("h4", null, "例句"));
  p.examples.forEach((ex) => sec.append(example(ex)));

  if (p.rewrite) {
    sec.append(el("h4", null, "改寫成 to／for"), el("p", "muted", p.rewrite.text));
    for (const [prep, desc, ex] of p.rewrite.rows) {
      sec.append(el("p", "rewrite-label", `用 ${prep}：${desc}`), example(ex));
    }
  }
  if (p.tip) sec.append(callout("c-tip", "💡", "小技巧", p.tip));
  sec.append(callout("c-warn", "⚠️", "常見錯誤", p.warn[0], p.warn[1]));
  if (p.info) {
    const box = callout("c-info", "ℹ", p.info[0], "");
    box.querySelector(".c-text")?.remove();
    const text = el("span", "c-text");
    p.info[1].split("\n").forEach((line, j) => {
      if (j) text.append(el("br"));
      text.append(line);
    });
    box.querySelector("div").append(text);
    sec.append(box);
  }
  wrap.append(sec);
});

// ---------- 容易混淆的句型 ----------
const COMPARE = [
  {
    title: "句型二（S + V + SC）vs 句型三（S + Vt + O）",
    point: "動詞後面都只有一個成分。和主詞「相等」的是補語，「不相等」的是受詞。",
    a: ["句型二：S + V + SC", { parts: [["She", "S"], ["is", "V"], ["a teacher", "SC"]], zh: "她是老師。（She ＝ a teacher）" }],
    b: ["句型三：S + Vt + O", { parts: [["She", "S"], ["met", "Vt"], ["a teacher", "O"]], zh: "她遇到一位老師。（She ≠ a teacher）" }],
  },
  {
    title: "句型四（S + Vt + O + OC）vs 句型五（S + Vt + IO + DO）",
    point: "動詞後面都有兩個成分。第二個成分和第一個「相等」的是受詞補語，「不相等」的是直接受詞。",
    a: ["句型四：S + Vt + O + OC", { parts: [["She", "S"], ["made", "Vt"], ["him", "O"], ["happy", "OC"]], zh: "她讓他很開心。（him ＝ happy）" }],
    b: ["句型五：S + Vt + IO + DO", { parts: [["She", "S"], ["made", "Vt"], ["him", "IO"], ["a cake", "DO"]], zh: "她做了一個蛋糕給他。（him ≠ a cake）" }],
  },
];
const cmp = document.getElementById("compare-list");
for (const c of COMPARE) {
  const box = el("div", "compare-box");
  box.append(el("h4", null, c.title), el("p", "muted", c.point));
  for (const [label, ex] of [c.a, c.b]) box.append(el("p", "rewrite-label", label), example(ex));
  cmp.append(box);
}
cmp.append(callout("c-tip", "💡", "小技巧：等號測試", "在兩個成分之間放一個等號，說得通就是「補語」，說不通就是「受詞」。"));

// 從分析頁點過來時，捲到對應的句型
if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
