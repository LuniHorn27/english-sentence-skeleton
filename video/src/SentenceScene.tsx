// 通用的「句子」段落：積木、中譯、等號測試、提示、字幕、英文朗讀都由 scenes.ts 的資料決定
import React from "react";
import { Easing, Html5Audio, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Block, type BlockState } from "./Block";
import { Formula, Frame, Subtitle } from "./Common";
import { C, ROLE, type Role } from "./theme";
import { compile, current } from "./timeline";
import type { SentenceSceneDef, TestDef } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const SentenceScene: React.FC<{ def: SentenceSceneDef }> = ({ def }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tl = React.useMemo(() => compile(def), [def]);
  const now = frame / fps;
  const since = (t: number) => frame - t * fps; // 從 t 秒到現在過了幾格
  const pop = (t: number, damping = 13) => (since(t) < 0 ? 0 : spring({ frame: since(t), fps, config: { damping } }));
  const fontSize = def.fontSize ?? 76;

  // 小測驗：答案公布前，積木是灰框、沒有標籤
  const revealP = def.quiz ? (tl.reveal === undefined ? 0 : interpolate(since(tl.reveal), [0, 12], [0, 1], clamp)) : 1;

  const blocks: (BlockState & { id: string })[] = def.blocks.map((b) => {
    const info = tl.block[b.id];
    const relabel = current(info.relabels.map((r) => ({ t: r.t, v: r.role as Role })), now);
    const role = relabel?.v ?? b.role;
    const shown = info.show === undefined ? -1 : since(info.show);
    const appear = shown < 0 ? 0 : spring({ frame: shown, fps, config: { damping: 12 } });
    const grow = interpolate(shown, [0, 0.35 * fps], [0, 1], clamp);
    const fade = info.hide === undefined ? 0 : interpolate(since(info.hide), [0, 0.6 * fps], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
    const pulse = Math.max(0, ...info.pulses.map((t) => (since(t) < 0 ? 0 : interpolate(since(t), [0, 8, 30], [0, 1, 0], clamp))), relabel ? interpolate(since(relabel.t), [0, 8, 30], [0, 1, 0], clamp) : 0);
    return {
      id: b.id,
      text: b.text,
      role,
      label: role === "M" ? b.label ?? "修飾語" : role,
      fontSize,
      appear,
      width: grow * (1 - fade),
      fade,
      badge: info.count && since(info.count.t) >= 0 && !(info.hide !== undefined && since(info.hide) >= 0) ? { n: info.count.n, p: pop(info.count.t, 10) } : undefined,
      pulse,
      color: revealP,
      labelOpacity: def.quiz ? revealP : 1,
    };
  });

  const zh = current(tl.zh, now);
  const chip = current(tl.chip, now);
  const test = current(tl.test, now);
  const sub = tl.subs.find((s) => now >= s.start && now < s.end);
  const big = current(tl.big, now);
  const countdown = current(tl.countdown, now);

  return (
    <Frame>
      <Title def={def} titles={tl.title} now={now} since={since} />

      {/* 句子、中譯、等號測試、提示：放在畫面中間偏上 */}
      <div style={{ position: "absolute", left: 0, right: 0, top: 230, bottom: 230, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 28 }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "flex-end", maxWidth: 1760 }}>
          {blocks.map((b) => (
            <Block key={b.id} {...b} />
          ))}
        </div>
        <div style={{ height: 64, fontSize: 46, color: C.text2, opacity: zh?.v ? interpolate(since(zh.t), [0, 10], [0, 1], clamp) : 0 }}>{zh?.v}</div>
        <div style={{ height: 130, display: "flex", alignItems: "center" }}>
          {test?.v ? (
            <TestRow test={test.v} defBlocks={blocks} since={since(test.t)} judgeSince={tl.judge === undefined ? -1 : since(tl.judge)} />
          ) : chip?.v ? (
            <Chip text={chip.v} p={pop(chip.t)} />
          ) : null}
        </div>
      </div>

      {countdown && since(countdown.t) < countdown.v * fps && <Countdown n={countdown.v} since={since(countdown.t)} />}
      {big?.v && <Big text={big.v} since={since(big.t)} />}
      <Subtitle text={sub?.text} since={sub ? since(sub.start) : 0} />

      {tl.says.map((s, i) => (
        <Sequence key={`en${i}`} from={Math.round(s.t * fps)} layout="none">
          <Html5Audio src={staticFile(`audio/${s.v}.wav`)} />
        </Sequence>
      ))}
      {tl.voices.map((s, i) => (
        <Sequence key={`zh${i}`} from={Math.round(s.t * fps)} layout="none">
          <Html5Audio src={staticFile(`voice/${s.v}.wav`)} />
        </Sequence>
      ))}
    </Frame>
  );
};

// 句型標題：開頭在畫面中央放大，1 秒後縮到左上角；中途換標題時淡入淡出
const Title: React.FC<{ def: SentenceSceneDef; titles: { t: number; v: string }[]; now: number; since: (t: number) => number }> = ({ def, titles, now, since }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!def.title) return null;
  const list = [{ t: 0, v: def.title }, ...titles];
  const cur = current(list, now)!;
  const p = interpolate(frame, [1.1 * fps, 1.8 * fps], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const left = interpolate(p, [0, 1], [960, 80]);
  const top = interpolate(p, [0, 1], [470, 56]);
  const shift = -50 * (1 - p);
  const scale = interpolate(p, [0, 1], [1.7, 1]);
  const intro = interpolate(frame, [0, 10], [0, 1], clamp);
  const fadeIn = cur.t > 0 ? interpolate(since(cur.t), [0, 12], [0, 1], clamp) : 1;
  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        transform: `translate(${shift}%, ${shift}%) scale(${scale})`,
        transformOrigin: `${-shift}% ${-shift}%`,
        opacity: intro,
        background: C.surface,
        border: `3px solid ${C.border}`,
        borderRadius: 20,
        padding: "14px 32px",
      }}
    >
      <div style={{ opacity: fadeIn }}>
        <Formula label={cur.v} size={56} />
      </div>
    </div>
  );
};

// 等號測試：先顯示「a ＝ b ？」，judge 時揭曉 ＝ ✓ 或 ≠ ✗
const TestRow: React.FC<{ test: TestDef; defBlocks: (BlockState & { id: string })[]; since: number; judgeSince: number }> = ({ test, defBlocks, since, judgeSince }) => {
  const { fps } = useVideoConfig();
  const a = defBlocks.find((b) => b.id === test.a)!;
  const b = defBlocks.find((x) => x.id === test.b)!;
  const enter = spring({ frame: since, fps, config: { damping: 14 } });
  const judged = judgeSince >= 0;
  const judgeP = judged ? spring({ frame: judgeSince, fps, config: { damping: 10 } }) : 0;
  const color = test.ok ? C.ok : C.danger;
  const mini = (x: BlockState) => (
    <span style={{ fontSize: 52, fontWeight: 600, color: ROLE[x.role].fg, background: ROLE[x.role].bg, border: `4px solid ${ROLE[x.role].line}`, borderRadius: 16, padding: "4px 24px 8px" }}>{x.text}</span>
  );
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 26, opacity: enter, transform: `translateY(${(1 - enter) * 30}px)`, background: C.surface, border: `3px solid ${C.border}`, borderRadius: 24, padding: "18px 36px" }}>
      {mini(a)}
      <span style={{ fontSize: 72, fontWeight: 700, width: 70, textAlign: "center", color: judged ? color : C.muted, transform: `scale(${judged ? 0.6 + 0.4 * judgeP : 1})` }}>
        {judged && !test.ok ? "≠" : "＝"}
      </span>
      {mini(b)}
      <span style={{ fontSize: 60, width: 70, textAlign: "center", color: judged ? color : C.muted, transform: `scale(${judged ? judgeP : 1})` }}>{judged ? (test.ok ? "✓" : "✗") : "？"}</span>
      <span style={{ fontSize: 44, fontWeight: 600, color, opacity: judgeP, whiteSpace: "nowrap" }}>{test.note}</span>
    </div>
  );
};

const Chip: React.FC<{ text: string; p: number }> = ({ text, p }) => (
  <div style={{ fontSize: 46, fontWeight: 600, color: C.text, background: C.surface, border: `3px solid ${C.border}`, borderRadius: 999, padding: "12px 40px", transform: `scale(${p})` }}>{text}</div>
);

// 小測驗倒數：3、2、1
const Countdown: React.FC<{ n: number; since: number }> = ({ n, since }) => {
  const { fps } = useVideoConfig();
  const left = n - Math.floor(since / fps);
  const inSec = (since % fps) / fps;
  return (
    <div style={{ position: "absolute", right: 150, top: 380, width: 170, height: 170, borderRadius: 999, border: `8px solid ${C.accent}`, background: C.surface, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 96, fontWeight: 700, color: C.accent, transform: `scale(${1.15 - 0.15 * Math.min(1, inSec * 4)})` }}>
      {left}
    </div>
  );
};

// 畫面中央的大字（例如開場的「五大句型」）
const Big: React.FC<{ text: string; since: number }> = ({ text, since }) => {
  const { fps } = useVideoConfig();
  const p = spring({ frame: since, fps, config: { damping: 14 } });
  return (
    <div style={{ position: "absolute", inset: 0, background: `rgba(250, 250, 248, ${0.94 * Math.min(1, p)})`, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontSize: 150, fontWeight: 800, letterSpacing: 12, transform: `scale(${0.8 + 0.2 * p})`, opacity: Math.min(1, p) }}>{text}</div>
    </div>
  );
};
