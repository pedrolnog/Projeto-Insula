import type { NextConfig } from "next";

const backendInternalUrl =
  process.env.BACKEND_INTERNAL_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendInternalUrl}/api/v1/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${backendInternalUrl}/media/:path*`,
      },
    ];
  },
};

export default nextConfig;
