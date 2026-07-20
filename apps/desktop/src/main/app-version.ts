/**
 * Lee la versión del producto desde el archivo `VERSION` de la raíz del repo
 * (fuente de verdad del monorepo; ver `npm run version:sync`).
 *
 * - Dev: `out/main` → 4 niveles arriba hasta la raíz del monorepo.
 * - Empaquetado: `resources/VERSION` (copiado vía electron-builder extraResources).
 *
 * Si el archivo no está disponible, cae a `app.getVersion()` (package.json
 * sincronizado con VERSION).
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { app } from 'electron'

const DEV_VERSION_FILE = join(__dirname, '../../../../VERSION')

export function resolveVersionFilePath(): string {
  if (app.isPackaged) {
    return join(process.resourcesPath, 'VERSION')
  }
  return DEV_VERSION_FILE
}

/** Versión semver del software según `VERSION` (o fallback a Electron). */
export function readAppVersion(): string {
  try {
    const raw = readFileSync(resolveVersionFilePath(), 'utf8').trim()
    if (raw.length > 0) return raw
  } catch {
    // archivo ausente o ilegible → fallback
  }
  return app.getVersion()
}
