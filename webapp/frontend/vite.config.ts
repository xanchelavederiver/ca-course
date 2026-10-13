/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev: the API runs separately (make web-dev); /api is proxied to it.
const api = process.env.API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: api, changeOrigin: false } },
  },
  build: {
    chunkSizeWarningLimit: 4000,
    rollupOptions: {
      output: {
        // big vendors in their own chunks (cached across app rebuilds)
        manualChunks(id) {
          if (id.includes("monaco-editor")) return "monaco";
          if (id.includes("mathjax-full")) return "mathjax";
          if (id.includes("pdfjs-dist") || id.includes("react-pdf")) return "pdf";
          if (id.includes("@mantine") || id.includes("@tabler")) return "ui";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
