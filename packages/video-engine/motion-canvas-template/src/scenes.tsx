import { Circle, Layout, Line, Txt, makeScene2D, waitUntil } from '@motion-canvas/2d';
import { createRef, easeInOutCubic, tween } from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  // CINEFORGE explainer starter: brand ring → title reveal → underline sweep
  const ring = createRef<Circle>();
  const title = createRef<Txt>();
  const line = createRef<Line>();

  view.add(
    <Layout layout direction={'column'} alignItems={'center'} gap={40}>
      <Circle ref={ring} size={140} stroke={'#7c5cff'} lineWidth={6} endAngle={0} />
      <Txt ref={title} fill={'#f5f5ff'} fontFamily={'Inter'} fontSize={72} opacity={0}>
        {'CINEFORGE'}
      </Txt>
      <Line ref={line} points={[[0, 0], [0, 0]]} stroke={'#00e5ff'} lineWidth={8} />
    </Layout>,
  );

  yield* tween(0.8, v => ring().endAngle(easeInOutCubic(v) * Math.PI * 2));
  yield* tween(0.6, v => title().opacity(v));
  yield* tween(0.5, v => line().points([[0, 0], [260 * easeInOutCubic(v), 0]]));
  yield* waitUntil('end');
});
