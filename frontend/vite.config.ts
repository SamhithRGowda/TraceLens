import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Minimal config on purpose: no proxy, no env-based API base yet.
// The backend URL is handled explicitly in src/api/client.ts instead,
// so it's obvious and greppable rather than hidden in build config.
export default defineConfig({
  plugins: [react()],
});
