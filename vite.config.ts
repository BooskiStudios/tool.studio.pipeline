/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * In development the browser only ever talks to Vite (http://localhost:5173). Vite forwards `/api`
 * to Booski Core, so the API is same-origin: the session cookie and CSRF token just work, and no CORS
 * configuration is needed. The Host header is kept (changeOrigin: false) so Booski Core's Origin
 * check sees the page's own origin.
 */
const apiTarget = process.env.BOOSKI_API_URL ?? "http://127.0.0.1:8000";
const apiProxy = { "/api": { target: apiTarget, changeOrigin: false } };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: apiProxy },
  preview: { port: 4173, strictPort: true, proxy: apiProxy },
  test: {
    environment: "jsdom",
    // HTTPS, so the test DOM accepts the Secure "__Host-" cookies Booski Core sets.
    environmentOptions: { jsdom: { url: "https://localhost/" } },
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
