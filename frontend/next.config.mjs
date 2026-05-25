/** @type {import('next').NextConfig} */
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://backend:8000";

const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // Proxy browser /api/* calls to the FastAPI backend. In production behind the
  // host nginx, nginx may route /api directly to the backend instead; this
  // rewrite keeps the app self-contained for local dev and previews.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` }];
  },
};

export default nextConfig;
