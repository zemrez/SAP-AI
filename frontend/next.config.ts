import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  // basePath and assetPrefix will be set for BSP deployment
  images: { unoptimized: true },
};

export default nextConfig;
