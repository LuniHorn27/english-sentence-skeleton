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
    { n: "p3.0", noSub: true, sec: 2.4 },
    { do: [{ show: ["s", "v", "o"] }, { say: "p3", at: 1.1 }, { zh: "我喜歡音樂。", at: 1.1 }] },
    { n: "p3.1", do: [{ count: ["o"] }, { chip: "動詞後面：1 塊" }] },
    { n: "p3.2" },
    { n: "p3.3", do: [{ test: { a: "s", b: "o", ok: false, note: "說不通 → 受詞" } }] },
    { n: "p3.4", do: [{ judge: true }] },
    { n: "p3.5", do: [{ pulse: ["o"] }] },
    { n: "p3.6", do: [{ pulse: ["v"] }] },
    { sec: 1 },
  ],
};
