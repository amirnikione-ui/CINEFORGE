import {AbsoluteFill} from 'remotion';

/**
 * Cinematic finishing layer rendered above all scenes:
 * - an inset box-shadow vignette that darkens the frame edges,
 * - two thin letterbox bars at the top and bottom of the frame.
 *
 * Purely static (no frame dependence) and non-interactive.
 */
export const VignetteOverlay = () => {
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{boxShadow: 'inset 0 0 240px 80px rgba(0, 0, 0, 0.8)'}}
      />
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '2.5%',
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '2.5%',
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
        }}
      />
    </AbsoluteFill>
  );
};
