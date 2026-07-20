#!/usr/bin/env node
/**
 * Fuente de verdad: archivo VERSION en la raíz del repo.
 * Sincroniza o verifica package.json (raíz, desktop) y backend/pyproject.toml.
 *
 * Uso:
 *   node packaging/version-sync.mjs          # escribe
 *   node packaging/version-sync.mjs --check  # falla si hay drift
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const checkOnly = process.argv.includes("--check");

const SEMVER = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;

function readVersionFile() {
  const raw = readFileSync(path.join(root, "VERSION"), "utf8").trim();
  if (!SEMVER.test(raw)) {
    throw new Error(`VERSION inválida: "${raw}" (se espera semver, p. ej. 0.2.0)`);
  }
  return raw;
}

function readJson(rel) {
  return JSON.parse(readFileSync(path.join(root, rel), "utf8"));
}

function writeJson(rel, data) {
  writeFileSync(path.join(root, rel), `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function readTomlVersion(rel) {
  const text = readFileSync(path.join(root, rel), "utf8");
  const match = text.match(/^version\s*=\s*"([^"]+)"/m);
  if (!match) {
    throw new Error(`No se encontró version = "..." en ${rel}`);
  }
  return match[1];
}

function writeTomlVersion(rel, version) {
  const file = path.join(root, rel);
  const text = readFileSync(file, "utf8");
  if (!/^version\s*=\s*"[^"]+"/m.test(text)) {
    throw new Error(`No se encontró version = "..." en ${rel}`);
  }
  writeFileSync(file, text.replace(/^version\s*=\s*"[^"]+"/m, `version = "${version}"`), "utf8");
}

const targets = [
  {
    id: "package.json",
    get: () => readJson("package.json").version,
    set: (version) => {
      const pkg = readJson("package.json");
      pkg.version = version;
      writeJson("package.json", pkg);
    },
  },
  {
    id: "apps/desktop/package.json",
    get: () => readJson("apps/desktop/package.json").version,
    set: (version) => {
      const pkg = readJson("apps/desktop/package.json");
      pkg.version = version;
      writeJson("apps/desktop/package.json", pkg);
    },
  },
  {
    id: "backend/pyproject.toml",
    get: () => readTomlVersion("backend/pyproject.toml"),
    set: (version) => writeTomlVersion("backend/pyproject.toml", version),
  },
];

const expected = readVersionFile();
const drifts = targets
  .map((t) => ({ id: t.id, actual: t.get() }))
  .filter((t) => t.actual !== expected);

if (checkOnly) {
  if (drifts.length > 0) {
    console.error(`VERSION=${expected} no coincide con:`);
    for (const d of drifts) {
      console.error(`  ${d.id}: ${d.actual}`);
    }
    console.error("Ejecuta: npm run version:sync");
    process.exit(1);
  }
  console.log(`OK: versión ${expected} sincronizada en todos los targets.`);
  process.exit(0);
}

for (const t of targets) {
  const before = t.get();
  if (before === expected) {
    console.log(`= ${t.id} (${before})`);
    continue;
  }
  t.set(expected);
  console.log(`→ ${t.id}: ${before} → ${expected}`);
}

console.log(`OK: VERSION ${expected} sincronizada.`);
