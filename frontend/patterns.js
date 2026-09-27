// 五大句型介紹頁：給初學者的編排
//   第 1 步 認識 4 個零件 → 第 2 步 一張圖看懂五大句型 → 第 3 步 逐一介紹（固定格式）→ 進階（收合）
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

// 一行 ✗／✓ 對照
function wrongRight(wrong, right) {
  const box = el("div", "wr");
  box.append(el("p", "wr-no", `✗ ${wrong}`), el("p", "wr-ok", `✓ ${right}`));
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

// ---------- 第 2 步：地圖 ----------
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

// ---------- 第 3 步：五個句型（固定格式） ----------
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
    mistake: ["He arrived the station.", "He arrived at the station.", "Vi 後面不能直接接名詞，要先加介系詞。"],
    more: [
      "文法書的名稱：完全不及物動詞。",
      "There is a cat under the table. 表示「有」，本網站把 is 標成 Vi，真正的主詞是 a cat。",
      "I am at school. 一般歸在句型一：am 表示「在」，at school 是地點修飾語（但不能省略）。也有文法書把 at school 當成主詞補語（句型二），考試時以傳統的句型一為主。",
    ],
  },
  {
    n: 3, name: "句型二", formula: "S + V + SC",
    point: "動詞後面接補語，說明主詞「是什麼」或「怎麼樣」。",
    labels: "SC＝主詞補語：主詞 ＝ SC",
    examples: [
      { parts: [["She", "S"], ["is", "V"], ["a nurse", "SC"]], zh: "她是護理師。（She ＝ a nurse）" },
      { parts: [["The soup", "S"], ["smells", "V"], ["good", "SC"]], zh: "這碗湯聞起來很香。（The soup ＝ good）" },
    ],
    verbs: "be（am、is、are）、look、sound、smell、taste、feel、become、get、turn、stay",
    mistake: ["She looks happily.", "She looks happy.", "補語要用形容詞，不能用副詞。"],
    more: [
      "文法書的名稱：不完全不及物動詞（又叫連綴動詞）。",
      "補語可以是名詞（a nurse），也可以是形容詞（good）。",
      "He looks happy.（看起來 → 句型二）；He looks at the picture.（看著 → 句型一，at the picture 是修飾語）。",
    ],
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
    mistake: ["We discussed about the problem.", "We discussed the problem.", "及物動詞後面直接接受詞，不要多加介系詞。"],
    more: [
      "文法書的名稱：完全及物動詞。",
      "受詞可以是名詞、代名詞，也可以是 V-ing（enjoy playing）、to V（want to go）或一個子句（I think that he is right）。",
      "被動語態：Mary wrote the letter. → The letter was written by Mary. 本網站標成「句型三（被動語態）」。",
    ],
  },
  {
    n: 5, name: "句型四", formula: "S + Vt + O + OC",
    point: "受詞後面再接補語，說明受詞「是什麼」或「變得怎樣」。",
    labels: "OC＝受詞補語：受詞 ＝ OC",
    examples: [
      { parts: [["The news", "S"], ["made", "Vt"], ["her", "O"], ["sad", "OC"]], zh: "這個消息讓她很難過。（her ＝ sad）" },
      { parts: [["We", "S"], ["named", "Vt"], ["our dog", "O"], ["Lucky", "OC"]], zh: "我們把狗取名叫 Lucky。（our dog ＝ Lucky）" },
    ],
    verbs: "make、keep、find、call、name、let、ask、tell",
    mistake: ["The teacher made us to clean the room.", "The teacher made us clean the room.", "make、let、have 後面接原形動詞，不加 to。"],
    more: [
      "文法書的名稱：不完全及物動詞。",
      "受詞補語可以是形容詞（sad）、名詞（Lucky）、原形動詞（let me go）或 to V（asked us to be quiet）。",
    ],
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
    mistake: ["He gave a book me.", "He gave a book to me.", "東西放前面時，人要用 to 或 for 帶出來。"],
    more: [
      "文法書的名稱：授與動詞。",
      "改寫：He gave me a book. → He gave a book to me.（to：東西送到對方手上，如 give、send、show、tell、teach、lend）",
      "改寫：My mom bought me a bike. → My mom bought a bike for me.（for：替對方做，如 buy、make、cook）",
      "改寫之後 to me、for me 是修飾語，句子變成句型三。",
    ],
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

  card.append(el("h3", "pcard-h", "⚠️ 常見錯誤"));
  card.append(wrongRight(p.mistake[0], p.mistake[1]), el("p", "pcard-why", p.mistake[2]));

  const more = el("details", "more");
  more.append(el("summary", null, "看更多"));
  const ul = el("ul", "more-list");
  p.more.forEach((m) => ul.append(el("li", null, m)));
  more.append(ul);
  card.append(more);
  wrap.append(card);
}

// ---------- 進階：動詞的五種分類 ----------
const adv = document.getElementById("advanced-body");
adv.append(el("p", null, "文法書依照「後面需要接什麼」把動詞分成五類，剛好對應五大句型："));
const VERB_TYPES = [
  ["完全不及物動詞", "不接東西", "句型一：S + Vi"],
  ["不完全不及物動詞", "主詞補語", "句型二：S + V + SC"],
  ["完全及物動詞", "一個受詞", "句型三：S + Vt + O"],
  ["不完全及物動詞", "受詞 ＋ 受詞補語", "句型四：S + Vt + O + OC"],
  ["授與動詞", "兩個受詞", "句型五：S + Vt + IO + DO"],
];
const table = el("div", "vtypes");
for (const [kind, needs, pattern] of VERB_TYPES) {
  const row = el("div", "vtype");
  row.append(el("span", "vtype-kind", kind), el("span", "vtype-needs", `＋ ${needs}`), el("span", "vtype-pattern", pattern));
  table.append(row);
}
adv.append(table);
const tips = el("ul", "more-list");
[
  "及物／不及物：看後面需不需要「受詞」。完全／不完全：看後面需不需要「補語」。",
  "快速判斷及物動詞：把中文意思放進「我＿他」和「他被我＿」。兩句都說得通（我喜歡他／他被我喜歡），通常是及物動詞。少數動詞中英文用法不同（listen 要說 listen to），最後仍以英文為準。",
  "同一個動詞可能有不同用法：He runs every morning.（跑步 → 句型一）；He runs a small shop.（經營 → 句型三）。",
].forEach((t) => tips.append(el("li", null, t)));
adv.append(tips);

// 從分析頁點過來時，捲到對應的句型
if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
