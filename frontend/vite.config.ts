import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // three.js and R3F ship as CJS; pre-bundle them so Vite doesn't
    // try to transform them on-the-fly in dev mode.
    include: ["three", "@react-three/fiber", "three-stdlib", "camera-controls"],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
