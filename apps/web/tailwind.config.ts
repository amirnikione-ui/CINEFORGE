import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#07070c',
          900: '#0b0b13',
          850: '#10101b',
          800: '#161624',
          700: '#1f1f31',
          600: '#2b2b42',
        },
        forge: {
          300: '#b7a6ff',
          400: '#9d86ff',
          500: '#7c5cff',
          600: '#6547e8',
        },
        neon: '#00e5ff',
      },
      boxShadow: {
        glow: '0 0 40px rgba(124, 92, 255, 0.25)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
export default config;
