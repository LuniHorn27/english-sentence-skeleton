import type { Role } from "./theme";

// 一塊積木：text 是英文，role 是角色；修飾語可以給 label（預設「修飾語」）
export type BlockDef = { id: string; text: string; role: Role; label?: string };

// 等號測試：a、b 是積木 id；ok＝說得通（補語）
export type TestDef = { a: string; b: string; ok: boolean; note: string };

// 每個動作都可以加 at（在這一拍開始後幾秒發生，預設 0）
export type Action = { at?: number } & (
  | { show: string[] } // 積木一塊一塊掉下來
  | { hide: string[] } // 積木縮小消失
  | { count: string[] } // 動詞後面的積木標上 1、2
  | { chip: string | null } // 句子下方的小提示，例如「動詞後面：0 塊」
  | { test: TestDef | null } // 等號測試：先出現「a ＝ b ？」
  | { judge: true } // 等號測試揭曉：＝ ✓ 或 ≠ ✗
  | { pulse: string[] } // 積木的標籤閃一下
  | { relabel: { id: string; role: Role } } // 換標籤（例如 DO → O）
  | { say: string } // 唸英文（sentences.json 的 key）
  | { zh: string | null } // 中文翻譯
  | { title: string } // 左上角的句型標題
  | { reveal: true } // 小測驗：積木上色、出現標籤
  | { countdown: number } // 小測驗：倒數
  | { big: string | null } // 畫面中央的大字
);

// 一拍：n 是旁白（narration.json 的 key），字幕和中文語音都用它；
// 長度自動配合旁白和英文朗讀，sec 是最短秒數；noSub＝只唸不顯示字幕（例如標題已經在畫面上）
export type Beat = { n?: string; sec?: number; noSub?: boolean; do?: Action[] };

export type SentenceSceneDef = {
  kind: "sentence";
  id: string;
  title?: string; // 開頭先放大顯示，再縮到左上角
  fontSize?: number; // 積木的英文字級，預設 76
  quiz?: boolean; // 小測驗：積木先不上色、不顯示標籤
  blocks: BlockDef[];
  beats: Beat[];
};
