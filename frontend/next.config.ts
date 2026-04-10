import type { NextConfig } from "next";

function getBackendUrl(): string | null {
  const backendUrl = process.env.BACKEND_URL?.trim();
  if (backendUrl) {
    return backendUrl.replace(/\/$/, "");
  }

  if (process.env.NODE_ENV === "development" && process.env.VERCEL !== "1") {
    return "http://localhost:8000";
  }

  return null;
}

const backendUrl = getBackendUrl();

const nextConfig: NextConfig = {
  async rewrites() {
    if (!backendUrl) {
      return [];
    }

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
