// 一塊積木：上方小標籤＋彩色方塊；可以掉下來、縮小消失、標數字、閃一下
import React from "react";
import { interpolateColors } from "remotion";
import { C, NEUTRAL, ROLE, type Role } from "./theme";

export type BlockState = {
  text: string;
  role: Role;
  label: string; // 標籤文字（修飾語是「修飾語」，其他是角色）
  fontSize: number;
  appear: number; // 0～1：掉下來的進度（可以稍微超過 1，彈一下）
  width: number; // 0～1：佔的寬度（出現、消失時讓整排句子平順地移動）
  fade: number; // 0～1：消失的進度
  badge?: { n: number; p: number }; // 數字 1、2 和彈出的進度
  pulse: number; // 0～1：閃一下的強度
  color: number; // 0～1：小測驗從灰框變成彩色
  labelOpacity: number;
};

// 估計積木的寬度（像素），用來做「佔位寬度」的動畫
export function estimateWidth(text: string, label: string, fontSize: number) {
  const textW = text.length * fontSize * 0.56 + 80;
  const labelW = label.length * fontSize * 0.5 + 40;
  return Math.max(textW, labelW) + 36;
}

export const Block: React.FC<BlockState> = (b) => {
  const role = ROLE[b.role];
  const isM = b.role === "M";
  const mix = (from: string, to: string) => interpolateColors(b.color, [0, 1], [from, to]);
  const bg = mix(NEUTRAL.bg, role.bg);
  const line = mix(NEUTRAL.line, role.line);
  const fg = mix(NEUTRAL.fg, role.fg);
  const maxWidth = estimateWidth(b.text, b.label, b.fontSize) * b.width;
  const drop = (1 - b.appear) * -140;
  const opacity = Math.min(1, Math.max(0, b.appear * 1.4)) * (1 - b.fade);

  return (
    <div style={{ maxWidth, flex: "0 0 auto", overflow: "hidden", padding: "30px 18px 10px" }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          opacity,
          transform: `translateY(${drop}px) scale(${1 - b.fade * 0.3})`,
          position: "relative",
        }}
      >
        <span
          style={{
            fontSize: b.fontSize * 0.42,
            fontWeight: 700,
            color: isM ? C.text2 : role.fg,
            background: isM ? C.surface2 : role.bg,
            border: `3px solid ${isM ? C.border : role.line}`,
            borderRadius: 999,
            padding: "2px 20px",
            opacity: b.labelOpacity,
            transform: `scale(${1 + 0.35 * b.pulse})`,
            whiteSpace: "nowrap",
          }}
        >
          {b.label}
        </span>
        <span
          style={{
            fontSize: b.fontSize,
            fontWeight: 600,
            color: isM ? C.text2 : fg,
            background: bg,
            border: `5px ${isM ? "dashed" : "solid"} ${line}`,
            borderRadius: 22,
            padding: "10px 34px 16px",
            whiteSpace: "nowrap",
            boxShadow: `0 6px 0 ${isM ? C.border : line}33, 0 0 0 ${14 * b.pulse}px ${role.line}40`,
          }}
        >
          {b.text}
        </span>
        {b.badge && (
          <span
            style={{
              position: "absolute",
              top: b.fontSize * 0.42 + 4,
              right: -14,
              width: 56,
              height: 56,
              borderRadius: 999,
              background: C.text,
              color: "#fff",
              fontSize: 34,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transform: `scale(${b.badge.p})`,
            }}
          >
            {b.badge.n}
          </span>
        )}
      </div>
    </div>
  );
};
