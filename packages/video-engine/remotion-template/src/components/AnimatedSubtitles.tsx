import { FC } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { clamp01, px } from "../theme";
import type { StoryboardPalette } from "../types";

/**
 * Narration subtitles at the bottom of the frame: word-by-word reveal timed
 * across the scene duration over a subtle translucent bar.
 */
export const AnimatedSubtitles: FC<{
  text: string;
  palette: StoryboardPalette;
  width: number;
  durationInFrames: number;
}> = ({ text, palette, width, durationInFrames }) => {
  const frame = useCurrentFrame();
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return null;
  }

  const start = Math.round(durationInFrames * 0.08);
  const end = Math.round(durationInFrames * 0.82);
  const wordsPerFrame = words.length / Math.max(1, end - start);
  const visibleFloat = (frame - start) * wordsPerFrame;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: px(140, width),
      }}
    >
      <div
        style={{
          maxWidth: width * 0.82,
          padding: `${px(18, width)}px ${px(32, width)}px`,
          background: "rgba(0, 0, 0, 0.35)",
          borderRadius: px(16, width),
          textAlign: "center",
          fontSize: px(40, width),
          lineHeight: 1.35,
          fontWeight: 600,
          color: palette.text,
        }}
      >
        {words.map((word, i) => (
          <span
            key={`${word}-${i}`}
            style={{
              display: "inline-block",
              marginRight: px(14, width),
              opacity: clamp01(visibleFloat - i),
            }}
          >
            {word}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
