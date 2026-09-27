// 影片每一段的內容。改字幕或例句時，docs/五大句型影片-分鏡腳本.md 也要一起改。
// 例句都先用網站的分析程式確認過標法（2026-09-28）。
import type { SentenceSceneDef } from "./types";

export const p3: SentenceSceneDef = {
  kind: "sentence",
  id: "p3",
  title: "句型三：S + Vt + O",
  blocks: [
    { id: "s", text: "I", role: "S" },
    { id: "v", text: "like", role: "Vt" },
    { id: "o", text: "music", role: "O" },
  ],
  beats: [
    { sec: 2.2 },
    { sec: 4, sub: "動詞後面也接 1 塊。", do: [{ show: ["s", "v", "o"] }, { say: "p3", at: 1.1 }, { zh: "我喜歡音樂。", at: 1.1 }] },
    { sec: 3.4, sub: "這次是受詞，還是補語？", do: [{ count: ["o"] }, { chip: "動詞後面：1 塊" }] },
    { sec: 5, sub: "放一個等號：I ＝ music？我不是音樂，說不通！", do: [{ test: { a: "s", b: "o", ok: false, note: "說不通 → 受詞" } }] },
    { sec: 4.2, sub: "說不通，它就是受詞 O：動作的對象。", do: [{ pulse: ["o"] }] },
    { sec: 4.6, sub: "Vt 是及物動詞：後面一定要有受詞。", do: [{ pulse: ["v"] }] },
    { sec: 1 },
  ],
};
