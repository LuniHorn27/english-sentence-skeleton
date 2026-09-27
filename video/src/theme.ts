// 顏色照抄網站的 frontend/style.css（淺色），影片和網站看起來一致
export const C = {
  bg: "#fafaf8",
  surface: "#ffffff",
  surface2: "#f1efe8",
  text: "#1f1f1d",
  text2: "#5f5e5a",
  muted: "#888780",
  border: "#d9d7cf",
  borderStrong: "#b4b2a9",
  ok: "#3b6d11",
  danger: "#a32d2d",
  accent: "#378add",
};

export type Role = "S" | "V" | "Vt" | "Vi" | "O" | "IO" | "DO" | "SC" | "OC" | "M";

type RoleColor = { bg: string; fg: string; line: string };
const S = { bg: "#e6f1fb", fg: "#0c447c", line: "#185fa5" };
const V = { bg: "#faece7", fg: "#712b13", line: "#993c1d" };
const O = { bg: "#e1f5ee", fg: "#085041", line: "#0f6e56" };
const K = { bg: "#faeeda", fg: "#633806", line: "#854f0b" };
const M = { bg: C.surface2, fg: C.text2, line: C.borderStrong };

export const ROLE: Record<Role, RoleColor> = {
  S, V, Vt: V, Vi: V, O, IO: O, DO: O, SC: K, OC: K, M,
};
export const NEUTRAL: RoleColor = { bg: C.surface, fg: C.text, line: C.borderStrong };

export const FONT = '-apple-system, BlinkMacSystemFont, "PingFang TC", "Noto Sans TC", sans-serif';
export const FPS = 30;
