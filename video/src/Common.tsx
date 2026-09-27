// 每一段都會用到的東西：背景外框、字幕、彩色公式
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT, ROLE, type Role } from "./theme";

// 背景＋右上角網站名稱＋進出場淡入淡出
export const Frame: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(frame, [0, 10, durationInFrames - 10, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ background: C.bg, fontFamily: FONT, color: C.text }}>
      <div style={{ position: "absolute", top: 48, right: 72, fontSize: 28, color: C.muted, letterSpacing: 2 }}>英文句子骨架分析</div>
      <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

// 字幕：畫面下方一行；換字幕時淡入
export const Subtitle: React.FC<{ text?: string; since: number }> = ({ text, since }) => {
  if (!text) return null;
  const opacity = interpolate(since, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 70, display: "flex", justifyContent: "center", opacity }}>
      <div
        style={{
          background: "rgba(31, 31, 29, 0.88)",
          color: "#fff",
          fontSize: 54,
          fontWeight: 500,
          padding: "18px 44px",
          borderRadius: 20,
          maxWidth: 1600,
          textAlign: "center",
          lineHeight: 1.4,
        }}
      >
        {text}
      </div>
    </div>
  );
};

const FORMULA_ROLES = new Set(Object.keys(ROLE));

// 「句型三：S + Vt + O」→ 句型名稱＋每個符號用角色顏色
export const Formula: React.FC<{ label: string; size: number }> = ({ label, size }) => {
  const [name, formula = ""] = label.split("：");
  return (
    <span style={{ fontSize: size, fontWeight: 700, whiteSpace: "nowrap" }}>
      <span>{name}：</span>
      {formula.split(" + ").map((tok, i) => {
        const color = FORMULA_ROLES.has(tok) ? ROLE[tok as Role].line : C.text;
        return (
          <span key={i}>
            {i > 0 && <span style={{ color: C.muted, fontWeight: 400 }}> + </span>}
            <span style={{ color }}>{tok}</span>
          </span>
        );
      })}
    </span>
  );
};
