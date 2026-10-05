import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

const isDocker = process.env.DOCKER === "true";
const apiTarget = isDocker ? "http://backend:8000" : "http://localhost:18081";
const wsTarget = isDocker ? "ws://backend:8000" : "ws://localhost:18081";

export default defineConfig({
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
} as never);
