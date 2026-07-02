import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "replicate.delivery" },
      { protocol: "https", hostname: "pbxt.replicate.delivery" },
      { protocol: "https", hostname: "*.replicate.com" },
      // Supabase Storage CDN
      { protocol: "https", hostname: "*.supabase.co" },
      // DigitalOcean Droplet static image server (Nginx)
      { protocol: "http", hostname: "localhost" },
      { protocol: "https", hostname: "*.personapress.io" },
    ],
  },
};

export default nextConfig;
