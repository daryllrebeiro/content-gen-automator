import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.DOCKER_BUILD === "true" ? "standalone" : undefined,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
    if (!backendUrl) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

