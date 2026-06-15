import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "replicate.delivery" },
      { protocol: "https", hostname: "pbxt.replicate.delivery" },
      // DigitalOcean Droplet static image server (Nginx)
      { protocol: "http", hostname: "localhost" },
      { protocol: "https", hostname: "*.personapress.io" },
    ],
  },
};

export default nextConfig;
