/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
  build: { chunkSizeWarningLimit: 1500 },
  test: { environment: "jsdom", include: ["src/**/*.test.tsx", "src/**/*.test.ts"], setupFiles: ["src/testSetup.ts"] },
});
