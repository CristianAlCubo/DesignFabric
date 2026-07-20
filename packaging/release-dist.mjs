#!/usr/bin/env node
/**
 * Script único de release: sincroniza versión, vendoriza `uv`, compila el
 * frontend y empaqueta con electron-builder, dejando solo los artefactos
 * finales (`.AppImage` / `.exe`) en `dist/`.
 *
 * A diferencia de ClearCut, NO hay paso de PyInstaller: el backend Python
 * (torch/diffusers/transformers son dependencias obligatorias, no opcionales
 * como en ClearCut) no se congela en build-time. En su lugar, el instalador
 * bundlea el código fuente + un `uv` standalone, y las dependencias se
 * instalan en el primer arranque de la app (ver `apps/desktop/src/main/pythonSetup.ts`).
 */
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, rmSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const desktopDir = path.join(root, "apps", "desktop");
const distDir = path.join(root, "dist");

function run(command, args, cwd = root) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
    env: process.env,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function readVersion() {
  return readFileSync(path.join(root, "VERSION"), "utf8").trim();
}

function assertArtifacts(version) {
  const expected = [
    `DesignFabric-${version}-x86_64.AppImage`,
    `DesignFabric-${version}-win-x64.exe`,
  ];
  const missing = expected.filter((name) => !existsSync(path.join(distDir, name)));
  if (missing.length > 0) {
    console.error("Faltan artefactos en dist/:");
    for (const name of missing) console.error(`  - ${name}`);
    if (existsSync(distDir)) {
      console.error("Contenido de dist/:", readdirSync(distDir));
    }
    process.exit(1);
  }
  console.log("\nArtefactos listos:");
  for (const name of expected) {
    console.log(`  dist/${name}`);
  }
}

mkdirSync(distDir, { recursive: true });

run("npm", ["run", "version:sync"]);
const version = readVersion();
console.log(`==> DesignFabric ${version} → dist/`);

// Descarga (si hace falta) los binarios standalone de `uv` para Linux/Windows
// que se bundlean en el instalador (ver electron-builder.yml → extraResources).
run("node", [path.join(root, "packaging", "vendor-uv.mjs")]);

run("npm", ["run", "build:app"]);

run(
  "npx",
  [
    "electron-builder",
    "--linux",
    "AppImage",
    "--win",
    "portable",
    "--x64",
    "--config",
    "electron-builder.yml",
  ],
  desktopDir,
);

for (const name of readdirSync(distDir)) {
  const full = path.join(distDir, name);
  if (name.endsWith(".AppImage") || name.endsWith(".exe")) continue;
  rmSync(full, { recursive: true, force: true });
}

assertArtifacts(version);
