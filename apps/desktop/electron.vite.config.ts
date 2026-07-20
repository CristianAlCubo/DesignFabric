import { resolve } from "node:path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// `@shared` expone código sin dependencias de Electron/React (tipos, contratos IPC)
// a los tres procesos por igual — ver `src/shared/`.
const sharedAlias = { "@shared": resolve("src/shared") };

export default defineConfig({
  main: {
    resolve: {
      alias: sharedAlias,
    },
    plugins: [externalizeDepsPlugin()],
  },
  preload: {
    resolve: { alias: sharedAlias },
    plugins: [externalizeDepsPlugin()],
  },
  renderer: {
    root: "src/renderer",
    resolve: {
      alias: {
        "@": resolve("src/renderer/src"),
        "@renderer": resolve("src/renderer/src"),
        ...sharedAlias,
      },
    },
    server: {
      open: false,
    },
    plugins: [react(), tailwindcss()],
  },
});
