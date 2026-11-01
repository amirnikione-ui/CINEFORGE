import { defineConfig } from "vite";
import motionCanvas from "@motion-canvas/vite-plugin";

// The plugin discovers src/project.ts by default (makeProject lives there).
export default defineConfig({
  plugins: [motionCanvas()],
});
