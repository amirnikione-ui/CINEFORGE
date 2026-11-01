import { FC } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { keywordLines } from "../content";
import { clamp01, px, rgba } from "../theme";
import type { SceneRenderProps } from "../types";

const LINE_STAGGER = 14;

// Keyword scene: up to 3 lines slide in from alternating sides while
// letter-spacing tightens (tracking-in animation).
export const TypographyScene: FC<SceneRenderProps> = ({ scene, palette, width }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lines = keywordLines(scene);

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        gap: px(42, width),
        padding: `0 ${px(90, width)}px`,
      }}
    >
      {lines.map((line, i) => {
        const enter = spring({
          frame: frame - i * LINE_STAGGER,
          fps,
          config: { damping: 17, stiffness: 120 },
        });
        const from = i % 2 === 0 ? -1 : 1;
        const tracking = interpolate(enter, [0, 1], [0.42, 0.06]);
        return (
          <span
            key={`${line}-${i}`}
            style={{
              display: "block",
              fontSize: px(76, width),
              fontWeight: 800,
              lineHeight: 1.15,
              color: i % 2 === 0 ? palette.text : palette.accent,
              textShadow: `0 0 ${px(36, width)}px ${rgba(palette.primary, 0.45)}`,
              letterSpacing: `${tracking}em`,
              opacity: clamp01(enter),
              transform: `translateX(${(1 - enter) * from * width * 0.28}px)`,
            }}
          >
            {line}
          </span>
        );
      })}
    </AbsoluteFill>
  );
};
