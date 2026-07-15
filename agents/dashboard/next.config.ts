import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // Convenience aliases — the real pages live at /docker-zone and /grafana.
  // permanent: false (307) so the browser URL bar updates but the alias is not
  // hard-cached, in case these routes move later.
  async redirects() {
    return [
      { source: '/docker', destination: '/docker-zone', permanent: false },
      { source: '/pricing', destination: '/grafana', permanent: false },
    ]
  },
};

export default nextConfig;
