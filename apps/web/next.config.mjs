/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The studio is a client-heavy app; API base is injected at build/runtime
  // via NEXT_PUBLIC_API_URL (see src/lib/api.ts).
};

export default nextConfig;
