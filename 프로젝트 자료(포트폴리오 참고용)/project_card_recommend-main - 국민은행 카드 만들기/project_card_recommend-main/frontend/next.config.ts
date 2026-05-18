import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "card.kbcard.com",
      },
      {
        protocol: "http",
        hostname: "card.kbcard.com",
      },
      {
        protocol: "https",
        hostname: "img1.kbcard.com",
      },
      {
        protocol: "http",
        hostname: "img1.kbcard.com",
      },
    ],
  },
};

export default nextConfig;
