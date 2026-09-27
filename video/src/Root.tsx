import React from "react";
import { Composition } from "remotion";
import { SentenceScene } from "./SentenceScene";
import { p3 } from "./scenes";
import { FPS } from "./theme";
import { sceneSeconds } from "./timeline";

export const RemotionRoot: React.FC = () => (
  <>
    {/* 樣品：只有「句型三：S + Vt + O」這一段 */}
    <Composition
      id="Sample"
      component={SentenceScene}
      defaultProps={{ def: p3 }}
      durationInFrames={Math.round(sceneSeconds(p3) * FPS)}
      fps={FPS}
      width={1920}
      height={1080}
    />
  </>
);
