import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",   // Required for Docker/Cloud Run deployment
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:3000"],
    },
  },
};

export default nextConfig;
