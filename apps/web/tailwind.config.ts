import type { Config } from "tailwindcss";

/**
 * CINEFORGE design language — "professional film studio, dark".
 * Background #07070c, panels #0d0d16 / #12121e, 1px borders #1e1e30,
 * accent gradient violet #7c5cff → cyan #00e5ff (used sparingly).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#07070c",
          panel: "#0d0d16",
          raised: "#12121e",
          line: "#1e1e30",
        },
        accent: {
          violet: "#7c5cff",
          cyan: "#00e5ff",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "Liberation Mono", "monospace"],
      },
      boxShadow: {
        panel: "0 8px 30px rgba(0, 0, 0, 0.45)",
        glow: "0 0 24px rgba(124, 92, 255, 0.25)",
      },
    },
  },
  plugins: [],
};

export default config;
