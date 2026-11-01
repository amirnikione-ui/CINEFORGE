import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CINEFORGE — AI Video Studio",
  description:
    "Describe the video. The agent directs, codes, and renders it — storyboard, narration, music, motion graphics and a finished cut from a single brief.",
};

export const viewport: Viewport = {
  themeColor: "#07070c",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-ink font-sans text-zinc-200 antialiased">{children}</body>
    </html>
  );
}
