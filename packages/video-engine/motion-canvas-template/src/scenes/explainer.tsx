import {Line, Rect, Txt, makeScene2D} from '@motion-canvas/2d';
import {createRef, waitFor} from '@motion-canvas/core';

/**
 * CINEFORGE Motion Canvas starter scene - a procedural title card.
 *
 * Motion Canvas is used at CINEFORGE for explainer-style 2D animation
 * (labeled diagrams, charts, step-by-step UI walkthroughs) while Remotion
 * handles promo/typography comps. The scene below exercises the core
 * building blocks an explainer needs: a full-screen background, tracked-out
 * title, growing accent rule, fading subtitle and a chart line that draws
 * itself in.
 *
 * Palette mirrors the storyboard contract (docs/API_CONTRACTS.md) so the
 * visual language stays consistent across engines.
 */
const BG = '#0a0a12';
const TEXT = '#f5f5ff';
const ACCENT = '#00e5ff';

/** Motion Canvas default render resolution. */
const STAGE_WIDTH = 1920;
const STAGE_HEIGHT = 1080;

/** Final polyline of the mini "chart". Kept short and readable. */
const chartPoints: [number, number][] = [
  [-240, 90],
  [-120, 40],
  [0, 110],
  [120, -50],
  [240, 20],
];

/** Collapsed starting points: every vertex sits on the baseline. */
const flatChartPoints: [number, number][] = chartPoints.map(([x]) => [x, 0]);

export default makeScene2D(function* (view) {
  const title = createRef<Txt>();
  const underline = createRef<Rect>();
  const subtitle = createRef<Txt>();
  const chart = createRef<Line>();

  view.add(<Rect width={STAGE_WIDTH} height={STAGE_HEIGHT} fill={BG} />);

  view.add(
    <Txt
      ref={title}
      text="CINEFORGE"
      fill={TEXT}
      fontSize={140}
      fontWeight={800}
      y={-160}
      opacity={0}
      letterSpacing={0}
    />,
  );

  view.add(
    <Rect
      ref={underline}
      width={0}
      height={6}
      radius={3}
      fill={ACCENT}
      y={-40}
    />,
  );

  view.add(
    <Txt
      ref={subtitle}
      text="Procedural explainers, rendered frame by frame"
      fill={TEXT}
      fontSize={48}
      y={40}
      opacity={0}
    />,
  );

  view.add(
    <Line
      ref={chart}
      points={flatChartPoints}
      stroke={ACCENT}
      lineWidth={6}
      lineCap="round"
      y={220}
    />,
  );

  // 1. Title fades in, then tracks out via a letter-spacing tween.
  yield* title().opacity(1, 0.6);
  yield* title().letterSpacing(24, 0.9);

  // 2. Accent rule grows from zero width.
  yield* underline().width(560, 0.7);

  // 3. Subtitle fades in.
  yield* subtitle().opacity(1, 0.6);

  // 4. Polyline draws in: the points tween from the flat baseline to the
  //    final chart shape (same vertex count, so Motion Canvas interpolates).
  yield* chart().points(chartPoints, 1.2);

  // Hold the finished card briefly before the scene ends.
  yield* waitFor(0.6);
});
