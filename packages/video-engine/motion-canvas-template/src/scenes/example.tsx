import { Layout, Rect, Txt, makeScene2D } from "@motion-canvas/2d";
import {
  all,
  createRef,
  createRefArray,
  easeOutCubic,
  tween,
  waitFor,
} from "@motion-canvas/core";

// Animated typography + bar-chart explainer: title tweens in, four bars grow
// with counting value labels, a caption closes the beat.
interface BarSpec {
  label: string;
  value: number;
}

const PALETTE = {
  bg: "#0a0a12",
  primary: "#7c5cff",
  accent: "#00e5ff",
  text: "#f5f5ff",
  muted: "#9aa0b5",
};

const BARS: BarSpec[] = [
  { label: "Storyboard", value: 92 },
  { label: "Motion", value: 78 },
  { label: "Render", value: 84 },
  { label: "Publish", value: 68 },
];

const BAR_MIN_H = 6;
const BAR_MAX_H = 380;

export default makeScene2D(function* (view) {
  view.fill(PALETTE.bg);

  const title = createRef<Txt>();
  const caption = createRef<Txt>();
  const bars = createRefArray<Rect>();
  const values = createRefArray<Txt>();

  view.add(
    <Layout layout direction={"column"} alignItems={"center"} gap={64}>
      <Txt ref={title} fontSize={64} fontWeight={800} fill={PALETTE.text} opacity={0}>
        {"CINEFORGE PIPELINE"}
      </Txt>
      <Layout layout direction={"row"} alignItems={"flex-end"} gap={40} height={440}>
        {BARS.map((spec) => (
          <Layout key={spec.label} layout direction={"column"} alignItems={"center"} gap={16}>
            <Txt ref={values} fontSize={30} fontWeight={700} fill={PALETTE.accent} opacity={0}>
              {"0%"}
            </Txt>
            <Rect ref={bars} width={104} height={BAR_MIN_H} radius={6} fill={PALETTE.primary} />
            <Txt fontSize={22} fill={PALETTE.muted}>
              {spec.label}
            </Txt>
          </Layout>
        ))}
      </Layout>
      <Txt ref={caption} fontSize={26} fill={PALETTE.muted} opacity={0}>
        {"From brief to render — every step is code."}
      </Txt>
    </Layout>,
  );

  // Title tweens in.
  yield* title().opacity(1, 0.6, easeOutCubic);

  // Bars grow one by one; value labels count up in lock-step.
  for (let i = 0; i < BARS.length; i++) {
    const target = BARS[i].value;
    yield* all(
      bars[i].height(BAR_MIN_H + (target / 100) * BAR_MAX_H, 0.7, easeOutCubic),
      values[i].opacity(1, 0.25),
      tween(0.7, (p) => {
        values[i].text(`${Math.round(p * target)}%`);
      }),
    );
  }

  // Caption closes the beat; a short hold lets the frame breathe.
  yield* caption().opacity(1, 0.5, easeOutCubic);
  yield* waitFor(1.2);
});
