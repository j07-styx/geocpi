import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5174,
    strictPort: true,
    proxy: {
      "/api/v2": { target: "http://127.0.0.1:8783", changeOrigin: false },
      "/api/viewer": { target: "http://127.0.0.1:8785", changeOrigin: false },
      "/api/geocpi": { target: "http://127.0.0.1:8786", changeOrigin: false }
    }
  }
});