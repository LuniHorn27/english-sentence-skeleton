// 五大句型介紹頁：給初學者的編排
//   第 1 步 認識 4 個零件 → 第 2 步 五個句型逐一介紹（固定格式）→ 第 3 步 用一張圖統整
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

// ---------- 第 1 步：4 個零件 ----------
const PARTS = [
  ["S", "主詞", "句子在說「誰」或「什麼」", "S"],
  ["V", "動詞", "主詞「做什麼」或「是什麼」", "V", "Vi 不及物　Vt 及物　V 後面接補語"],
  ["O", "受詞", "動作的對象", "O", "IO 給誰　DO 給什麼"],
  ["C", "補語", "補充說明主詞或受詞", "C", "SC 說明主詞　OC 說明受詞"],
];
const parts = document.getElementById("parts");
for (const [tag, name, desc, group, sub] of PARTS) {
  const card = el("div", `part r-${group}`);
  card.append(el("span", "part-tag", tag), el("span", "part-name", name), el("span", "part-desc", desc));
  if (sub) card.append(el("span", "part-sub", sub));
  parts.append(card);
}

// ---------- 第 3 步：統整地圖 ----------
// n 是程式的內部代號（網址 #p 後面的數字）
const MAP = [
  { title: "後面不接東西", cells: [{ n: 1, name: "句型一", formula: "S + Vi", ex: "Birds fly." }] },
  {
    title: "後面接 1 個東西",
    cells: [
      { n: 3, name: "句型二", formula: "S + V + SC", ex: "She is a nurse.", test: "S ＝ SC" },
      { n: 2, name: "句型三", formula: "S + Vt + O", ex: "I like music.", test: "S ≠ O" },
    ],
  },
  {
    title: "後面接 2 個東西",
    cells: [
      { n: 5, name: "句型四", formula: "S + Vt + O + OC", ex: "The news made her sad.", test: "O ＝ OC" },
      { n: 4, name: "句型五", formula: "S + Vt + IO + DO", ex: "He gave me a book.", test: "IO ≠ DO" },
    ],
  },
];
const pmap = document.getElementById("pmap");
for (const row of MAP) {
  const r = el("div", "pmap-row");
  r.append(el("div", "pmap-q", row.title));
  const cells = el("div", `pmap-cells n${row.cells.length}`);
  for (const c of row.cells) {
    const a = el("a", "pmap-cell");
    a.href = `#p${c.n}`;
    a.append(el("span", "pmap-name", c.name), el("span", "pmap-formula", c.formula));
    if (c.test) a.append(el("span", "pmap-test", c.test));
    a.append(el("span", "pmap-ex", c.ex));
    cells.append(a);
  }
  r.append(cells);
  pmap.append(r);
}

// ---------- 第 2 步：五個句型（固定格式） ----------
const PATTERNS = [
  {
    n: 1, name: "句型一", formula: "S + Vi",
    point: "動詞說完，意思就完整了。",
    labels: "Vi＝不及物動詞：後面不需要受詞",
    examples: [
      { parts: [["Birds", "S"], ["fly", "Vi"]], zh: "鳥會飛。" },
      { parts: [["The baby", "S"], ["is sleeping", "Vi"], ["in her room", "M", "副詞・表地點"]], zh: "寶寶在房間裡睡覺。（in her room 是修飾語）" },
    ],
    verbs: "go、come、run、walk、swim、sleep、cry、laugh、smile、arrive、happen",
  },
  {
    n: 3, name: "句型二", formula: "S + V + SC",
    point: "動詞後面接補語，說明主詞「是什麼」或「怎麼樣」。",
    labels: "SC＝主詞補語：補充說明主詞 S（S ＝ SC）",
    examples: [
      { parts: [["She", "S"], ["is", "V"], ["a nurse", "SC"]], zh: "她是護理師。（She ＝ a nurse）" },
      { parts: [["The soup", "S"], ["smells", "V"], ["good", "SC"]], zh: "這碗湯聞起來很香。（The soup ＝ good）" },
    ],
    verbs: "be（am、is、are）、look、sound、smell、taste、feel、become、get、turn、stay",
  },
  {
    n: 2, name: "句型三", formula: "S + Vt + O",
    point: "動詞後面接一個受詞，也就是動作的對象。",
    labels: "Vt＝及物動詞：後面一定要有受詞",
    examples: [
      { parts: [["I", "S"], ["like", "Vt"], ["music", "O"]], zh: "我喜歡音樂。（I ≠ music）" },
      { parts: [["They", "S"], ["enjoy", "Vt"], ["playing basketball", "O"]], zh: "他們喜歡打籃球。" },
    ],
    verbs: "like、want、need、have、buy、read、eat、see、enjoy、finish",
  },
  {
    n: 5, name: "句型四", formula: "S + Vt + O + OC",
    point: "受詞後面再接補語，說明受詞「是什麼」或「變得怎樣」。",
    labels: "OC＝受詞補語：補充說明受詞 O（O ＝ OC）",
    examples: [
      { parts: [["The news", "S"], ["made", "Vt"], ["her", "O"], ["sad", "OC"]], zh: "這個消息讓她很難過。（her ＝ sad）" },
      { parts: [["We", "S"], ["named", "Vt"], ["our dog", "O"], ["Lucky", "OC"]], zh: "我們把狗取名叫 Lucky。（our dog ＝ Lucky）" },
    ],
    verbs: "make、keep、find、call、name、let、ask、tell",
  },
  {
    n: 4, name: "句型五", formula: "S + Vt + IO + DO",
    point: "動詞後面接兩個受詞：先接「人」，再接「東西」。",
    labels: "IO＝間接受詞（給誰）　DO＝直接受詞（給什麼）",
    examples: [
      { parts: [["He", "S"], ["gave", "Vt"], ["me", "IO"], ["a book", "DO"]], zh: "他給我一本書。（me ≠ a book）" },
      { parts: [["My mom", "S"], ["bought", "Vt"], ["me", "IO"], ["a new bike", "DO"]], zh: "媽媽買了一輛新腳踏車給我。" },
    ],
    verbs: "give、send、show、tell、teach、lend、buy、make、cook",
  },
];

// 依賴世雄的編號排列
const wrap = document.getElementById("patterns");
for (const n of [1, 3, 2, 5, 4]) {
  const p = PATTERNS.find((x) => x.n === n);
  const card = el("article", "pcard");
  card.id = `p${p.n}`;
  const head = el("div", "pcard-head");
  head.append(el("span", "pcard-name", p.name), el("span", "pcard-formula", p.formula));
  card.append(head, el("p", "pcard-point", p.point), el("p", "pcard-labels", p.labels));

  card.append(el("h3", "pcard-h", "例句"));
  p.examples.forEach((ex) => card.append(example(ex)));

  card.append(el("h3", "pcard-h", "常見動詞"), el("p", "pcard-verbs", p.verbs));

  wrap.append(card);
}

// 從分析頁點過來時，捲到對應的句型
if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
