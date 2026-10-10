import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: true },
  build: {
    target: "es2020",
    rollupOptions: {
      output: {
        // Stable vendor chunks: an app update re-downloads only our code, not React or Leaflet.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query"],
          map: ["leaflet", "react-leaflet"],
        },
      },
    },
  },
});
