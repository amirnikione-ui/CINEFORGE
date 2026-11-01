import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

import type {Palette} from '../schema';
import {hexToRgba} from '../utils';

type GradientBackdropProps = {
  palette: Palette;
};

/**
 * Full-frame animated gradient backdrop built purely from layered CSS
 * gradients - no images, no fonts, no network access at render time.
 *
 * The two radial "light blobs" drift slowly as a function of the current
 * frame (time-based, fps-corrected), which keeps every render deterministic.
 * A repeating-linear-gradient scanline layer adds a subtle film-grain-like
 * texture at very low opacity.
 */
export const GradientBackdrop = ({palette}: GradientBackdropProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = fps > 0 ? frame / fps : 0;

  const driftA = Math.sin(seconds * 0.18);
  const driftB = Math.cos(seconds * 0.13);
  const driftC = Math.sin(seconds * 0.09 + 1.7);

  return (
    <AbsoluteFill style={{backgroundColor: palette.bg}}>
      <AbsoluteFill
        style={{
          background: `linear-gradient(165deg, ${hexToRgba(palette.primary, 0.18)} 0%, rgba(0, 0, 0, 0) 46%, ${hexToRgba(palette.accent, 0.12)} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(52% 38% at ${(28 + driftA * 10).toFixed(2)}% ${(26 + driftB * 8).toFixed(2)}%, ${hexToRgba(palette.primary, 0.32)}, rgba(0, 0, 0, 0) 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(46% 34% at ${(72 + driftC * 8).toFixed(2)}% ${(76 + driftA * 6).toFixed(2)}%, ${hexToRgba(palette.accent, 0.22)}, rgba(0, 0, 0, 0) 72%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            'repeating-linear-gradient(115deg, rgba(255, 255, 255, 0.03) 0px, rgba(255, 255, 255, 0.03) 1px, rgba(0, 0, 0, 0) 1px, rgba(0, 0, 0, 0) 3px)',
          backgroundPosition: `${(frame * 0.6) % 3}px 0px`,
        }}
      />
    </AbsoluteFill>
  );
};
