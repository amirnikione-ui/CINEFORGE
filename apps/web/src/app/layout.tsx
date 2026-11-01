import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CINEFORGE — AI Video Studio',
  description:
    'Chat with a director-agent: script, storyboard, code-driven motion, FFmpeg editing, final cut.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-ink-950 text-slate-200 antialiased">{children}</body>
    </html>
  );
}
