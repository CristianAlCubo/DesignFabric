/**
 * Shim para que el CLI de shadcn detecte un proyecto Vite.
 * El build real de la app usa `electron.vite.config.ts` vía electron-vite.
 */
import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve("src/renderer/src"),
      "@renderer": resolve("src/renderer/src"),
      "@shared": resolve("src/shared"),
    },
  },
});
