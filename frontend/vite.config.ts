import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";

// Default for the %VITE_CSP_EXTRA% placeholder in index.html (extra connect-src
// origins for non-localhost deployments). Derives the origins from
// VITE_API_BASE_URL / VITE_WS_URL so a deployed build always permits calls to
// its own API — otherwise the browser blocks every fetch behind CSP and the SPA
// (Google button, health checks, API calls) silently breaks. An explicit
// VITE_CSP_EXTRA still wins so docker-compose.tunnel.yml keeps working.
function cspConnectOrigins(env: Record<string, string>): string {
  const explicit = env.VITE_CSP_EXTRA;
  if (explicit !== undefined && explicit.trim() !== "") return explicit;

  const origins = new Set<string>();
  for (const raw of [env.VITE_API_BASE_URL, env.VITE_WS_URL]) {
    if (!raw) continue;
    let url: URL;
    try {
      url = new URL(raw);
    } catch {
      continue; // relative or malformed — same-origin, nothing to add
    }
    if (!["http:", "https:", "ws:", "wss:"].includes(url.protocol)) continue;
    const secure = url.protocol === "https:" || url.protocol === "wss:";
    // CSP matches on scheme: https://… does not allow wss://…, so add both.
    origins.add(`${secure ? "https" : "http"}://${url.host}`);
    origins.add(`${secure ? "wss" : "ws"}://${url.host}`);
  }
  return [...origins].join(" ");
}

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ""), ...process.env };
  process.env.VITE_CSP_EXTRA = cspConnectOrigins(env);

  const isDocker = process.env.DOCKER === "true";
  const apiTarget = isDocker ? "http://backend:8000" : "http://localhost:18081";
  const wsTarget = isDocker ? "ws://backend:8000" : "ws://localhost:18081";

  return {
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5174,
    // Allow Cloudflare Quick Tunnel hosts for temporary public demos
    // (matches any *.trycloudflare.com; dev server only).
    allowedHosts: [".trycloudflare.com"],
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/media": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/ws": {
        target: wsTarget,
        ws: true,
      },
    },
  },
  build: {
    minify: "esbuild",
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query"],
          ui: ["@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", "@radix-ui/react-select", "@radix-ui/react-tabs", "@radix-ui/react-toast", "@radix-ui/react-tooltip"],
          map: ["leaflet", "react-leaflet", "leaflet.markercluster"],
          charts: ["recharts"],
          forms: ["react-hook-form", "@hookform/resolvers", "zod"],
          state: ["zustand"],
          icons: ["lucide-react"],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}", "src/**/*.test.{ts,tsx}"],
  },
  } as never;
});
