#!/usr/bin/env node
/**
 * Descarga los binarios standalone de `uv` (Linux x64 + Windows x64) que se
 * bundlean con el instalador Electron (ver `apps/desktop/electron-builder.yml`
 * → `extraResources` → `packaging/vendor/uv/...`).
 *
 * `uv` publica binarios precompilados sin dependencias en GitHub Releases de
 * `astral-sh/uv`. Los assets relevantes son:
 *   - uv-x86_64-unknown-linux-gnu.tar.gz  (Linux x64)
 *   - uv-x86_64-pc-windows-msvc.zip       (Windows x64)
 *
 * Versión vendorizada: se fija UV_VERSION abajo como constante (en vez de
 * "latest") para que el build sea reproducible y no cambie de un día para
 * otro sin que alguien lo decida explícitamente. Se eligió la misma versión
 * que la instalada localmente en la máquina de desarrollo al escribir este
 * script (`uv --version` → 0.11.16) para máxima consistencia entre el `uv`
 * usado en dev y el que se bundlea. Para actualizar: cambiar esta constante
 * y volver a correr `node packaging/vendor-uv.mjs --force`.
 *
 * Idempotente: si el binario ya existe, no se vuelve a descargar (a menos
 * que se pase `--force`). Requiere conexión a internet la primera vez que
 * se corre para cada versión; si no hay red, falla con un mensaje claro (no
 * falla silenciosamente).
 */
import { createWriteStream, existsSync, readdirSync, statSync } from "node:fs";
import { chmod, mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const UV_VERSION = "0.11.16";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const vendorDir = path.join(root, "packaging", "vendor", "uv");
const force = process.argv.includes("--force");

const TARGETS = [
  {
    id: "linux-x64",
    assetName: `uv-x86_64-unknown-linux-gnu.tar.gz`,
    archiveKind: "tar.gz",
    // Dentro del tarball, `uv` viene en `uv-x86_64-unknown-linux-gnu/uv`.
    memberBinary: "uv",
    destDir: path.join(vendorDir, "linux-x64"),
    destBinary: "uv",
    executable: true,
  },
  {
    id: "win-x64",
    assetName: `uv-x86_64-pc-windows-msvc.zip`,
    archiveKind: "zip",
    memberBinary: "uv.exe",
    destDir: path.join(vendorDir, "win-x64"),
    destBinary: "uv.exe",
    executable: false,
  },
];

function downloadUrl(assetName) {
  return `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${assetName}`;
}

async function downloadToFile(url, destPath) {
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok || !response.body) {
    throw new Error(`Descarga falló (${response.status} ${response.statusText}): ${url}`);
  }
  await pipeline(response.body, createWriteStream(destPath));
}

async function extractTarGz(archivePath, extractDir) {
  const result = spawnSync("tar", ["-xzf", archivePath, "-C", extractDir], { stdio: "inherit" });
  if (result.status !== 0) {
    throw new Error(`No se pudo extraer ${archivePath} (¿falta el comando 'tar'?)`);
  }
}

async function extractZip(archivePath, extractDir) {
  // `unzip` en Linux/mac; en Windows se podría usar PowerShell Expand-Archive,
  // pero este script está pensado para correr en un entorno Linux de CI/dev
  // (cross-building el asset de Windows, que es solo un binario a copiar).
  let result = spawnSync("unzip", ["-o", archivePath, "-d", extractDir], { stdio: "inherit" });
  if (result.status !== 0) {
    // Fallback a PowerShell si estamos en Windows y no hay `unzip`.
    result = spawnSync(
      "powershell",
      ["-NoProfile", "-Command", `Expand-Archive -Force -Path '${archivePath}' -DestinationPath '${extractDir}'`],
      { stdio: "inherit" },
    );
    if (result.status !== 0) {
      throw new Error(`No se pudo extraer ${archivePath} (faltan 'unzip' y 'powershell')`);
    }
  }
}

function findFileRecursive(dir, fileName) {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      const found = findFileRecursive(full, fileName);
      if (found) return found;
    } else if (entry === fileName) {
      return full;
    }
  }
  return null;
}

async function vendorTarget(target) {
  const destPath = path.join(target.destDir, target.destBinary);
  if (existsSync(destPath) && !force) {
    console.log(`= ${target.id}: ya existe (${destPath}), omitiendo descarga.`);
    return;
  }

  console.log(`==> Vendorizando uv ${UV_VERSION} para ${target.id}…`);
  await mkdir(target.destDir, { recursive: true });

  const tmpDir = await mkdtemp(path.join(tmpdir(), "vendor-uv-"));
  try {
    const archivePath = path.join(tmpDir, target.assetName);
    const url = downloadUrl(target.assetName);
    console.log(`   descargando ${url}`);
    await downloadToFile(url, archivePath);

    const extractDir = path.join(tmpDir, "extracted");
    await mkdir(extractDir, { recursive: true });
    if (target.archiveKind === "tar.gz") {
      await extractTarGz(archivePath, extractDir);
    } else {
      await extractZip(archivePath, extractDir);
    }

    const found = findFileRecursive(extractDir, target.memberBinary);
    if (!found) {
      throw new Error(`No se encontró '${target.memberBinary}' dentro de ${target.assetName} tras extraer.`);
    }

    await rm(destPath, { force: true });
    const { copyFile } = await import("node:fs/promises");
    await copyFile(found, destPath);

    if (target.executable) {
      await chmod(destPath, 0o755);
    }

    console.log(`   OK: ${destPath}`);
  } finally {
    await rm(tmpDir, { recursive: true, force: true });
  }
}

async function main() {
  await mkdir(vendorDir, { recursive: true });
  for (const target of TARGETS) {
    await vendorTarget(target);
  }
  console.log("\nListo: binarios de uv vendorizados en packaging/vendor/uv/.");
}

main().catch((err) => {
  console.error("\nFalló la vendorización de uv:");
  console.error(err instanceof Error ? err.message : err);
  console.error(
    "\nEsto normalmente significa que no hay conexión a internet, o que GitHub Releases " +
      "no es alcanzable desde este entorno. Vuelve a correr 'node packaging/vendor-uv.mjs' " +
      "con red disponible.",
  );
  process.exit(1);
});
