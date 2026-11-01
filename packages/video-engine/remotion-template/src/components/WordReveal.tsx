import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

type WordRevealProps = {
  /** The word to render. Rendered verbatim, never re-cased. */
  word: string;
  /** Delay in frames before the word starts animating. */
  delay: number;
  /** Font size in pixels. */
  fontSize: number;
  /** Text color (the caller decides, e.g. accent for the last word). */
  color: string;
  /** Font family stack chosen by the parent composition. */
  fontFamily: string;
};

/**
 * Per-word cinematic reveal: a critically damped spring
 * (config damping 200 - no overshoot) drives opacity, translateY and scale.
 * Frames before `delay` resolve to the spring's initial value, so the word
 * simply sits invisible until its cue.
 */
const WordReveal = ({word, delay, fontSize, color, fontFamily}: WordRevealProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: {damping: 200},
  });

  const opacity = progress;
  const translateY = interpolate(progress, [0, 1], [46, 0]);
  const scale = interpolate(progress, [0, 1], [0.86, 1]);

  return (
    <span
      style={{
        display: 'inline-block',
        opacity,
        transform: `translateY(${translateY.toFixed(2)}px) scale(${scale.toFixed(4)})`,
        fontSize,
        color,
        fontFamily,
        fontWeight: 900,
        lineHeight: 1.04,
        letterSpacing: '-0.02em',
        willChange: 'opacity, transform',
      }}
    >
      {word}
    </span>
  );
};

export default WordReveal;
