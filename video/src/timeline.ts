// 把一段的「拍子」展開成有絕對時間（秒）的事件，畫面每一格都從這裡查狀態
import englishDurations from "./audio-durations.json";
import narration from "./narration.json";
import voiceDurations from "./voice-durations.json";
import type { Action, Beat, SentenceSceneDef } from "./types";

export type Timed<T> = { t: number } & T;

const EN = englishDurations as Record<string, number>;
const VOICE = voiceDurations as Record<string, number>;
export const NARRATION = narration as Record<string, string>;
export const VOICE_START = 0.15; // 每一拍開始後多久開始唸旁白

// 一拍要幾秒：旁白唸完、英文唸完、積木掉完，取最長的，再留一點空檔
export function beatSeconds(beat: Beat) {
  let sec = beat.sec ?? 0;
  if (beat.n) sec = Math.max(sec, VOICE_START + (VOICE[beat.n] ?? NARRATION[beat.n].length / 4.5) + 0.45);
  for (const a of beat.do ?? []) {
    const at = a.at ?? 0;
    if ("say" in a) sec = Math.max(sec, at + (EN[a.say] ?? 2) + 0.6);
    if ("show" in a) sec = Math.max(sec, at + a.show.length * 0.35 + 0.8);
  }
  return sec;
}

export function sceneSeconds(def: { beats: Beat[] }) {
  return def.beats.reduce((sum, b) => sum + beatSeconds(b), 0);
}

export function compile(def: SentenceSceneDef) {
  const actions: Timed<{ a: Action }>[] = [];
  const subs: { start: number; end: number; text: string }[] = [];
  const voices: { t: number; v: string }[] = [];
  let t = 0;
  for (const beat of def.beats) {
    const sec = beatSeconds(beat);
    if (beat.n) {
      voices.push({ t: t + VOICE_START, v: beat.n });
      if (!beat.noSub) subs.push({ start: t, end: t + sec, text: NARRATION[beat.n] });
    }
    for (const a of beat.do ?? []) actions.push({ t: t + (a.at ?? 0), a });
    t += sec;
  }
  actions.sort((x, y) => x.t - y.t);

  const block: Record<string, { show?: number; hide?: number; count?: { t: number; n: number }; pulses: number[]; relabels: Timed<{ role: string }>[] }> = {};
  for (const b of def.blocks) block[b.id] = { pulses: [], relabels: [] };

  // 同一個動作列出好幾塊積木時，一塊接一塊出現（間隔 0.35 秒）
  const STAGGER = 0.35;
  const latest = <K extends string>(key: K) => actions.filter((x) => key in x.a).map((x) => ({ t: x.t, v: (x.a as Record<K, unknown>)[key] }));

  for (const { t, a } of actions) {
    if ("show" in a) a.show.forEach((id, i) => (block[id].show ??= t + i * STAGGER));
    if ("hide" in a) a.hide.forEach((id, i) => (block[id].hide = t + i * STAGGER));
    if ("count" in a) a.count.forEach((id, i) => (block[id].count = { t: t + i * STAGGER, n: i + 1 }));
    if ("pulse" in a) a.pulse.forEach((id, i) => block[id].pulses.push(t + i * STAGGER));
    if ("relabel" in a) block[a.relabel.id].relabels.push({ t, role: a.relabel.role });
  }

  return {
    seconds: t,
    subs,
    block,
    says: latest("say") as { t: number; v: string }[],
    voices,
    judge: latest("judge")[0]?.t,
    zh: latest("zh") as { t: number; v: string | null }[],
    chip: latest("chip") as { t: number; v: string | null }[],
    test: latest("test") as { t: number; v: import("./types").TestDef | null }[],
    title: latest("title") as { t: number; v: string }[],
    reveal: latest("reveal")[0]?.t,
    countdown: latest("countdown") as { t: number; v: number }[],
    big: latest("big") as { t: number; v: string | null }[],
  };
}

// 目前（now 秒）最後一次設定的值，以及它是幾秒前設定的
export function current<T>(list: { t: number; v: T }[], now: number): { t: number; v: T } | undefined {
  let found;
  for (const x of list) if (x.t <= now) found = x;
  return found;
}
