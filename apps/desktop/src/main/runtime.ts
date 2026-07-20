/**
 * Resuelve las rutas del entorno Python del backend según el modo de
 * ejecución (desarrollo vs. build empaquetada) — usado tanto por
 * `backend-process.ts` (para lanzar uvicorn) como por `pythonSetup.ts`
 * (para el flujo de primer arranque en producción).
 *
 * - Dev (`npm run dev`): usa el `uv` del PATH del sistema y el `backend/`
 *   del propio repo (el desarrollador ya corrió `uv sync --extra dev` a
 *   mano). Comportamiento IDÉNTICO al actual, sin cambios.
 * - Empaquetado: usa el binario `uv` standalone bundleado en
 *   `resources/uv/uv[.exe]` (ver `electron-builder.yml` → `extraResources`)
 *   y un proyecto Python copiado a una carpeta escribible en
 *   `app.getPath('userData')` — el código fuente bundleado en
 *   `resources/backend` es de solo lectura y no puede alojar un `.venv`.
 */

import { join } from 'node:path'
import { app } from 'electron'

export interface BackendRuntime {
  /** Ruta al ejecutable `uv` a usar (del sistema en dev, bundleado en producción). */
  uvBin: string
  /** Carpeta del proyecto Python sobre la que correr `uv sync`/`uv run` (código fuente + venv). */
  projectDir: string
  /** true si es una build empaquetada (requiere el flujo de primer arranque). */
  isPackaged: boolean
}

/**
 * `__dirname` en runtime empaquetado y en dev apunta a `apps/desktop/out/main`
 * (electron-vite compila `src/main` a `out/main`). En dev, el backend Python
 * vive en la raíz del monorepo, 4 niveles de `..` más arriba:
 *
 *   out/main (__dirname) -> out -> desktop -> apps -> DesignFabricV2 -> backend
 */
const DEV_BACKEND_DIR = join(__dirname, '../../../../backend')

export function resolveBackendRuntime(): BackendRuntime {
  if (!app.isPackaged) {
    return {
      uvBin: 'uv',
      projectDir: DEV_BACKEND_DIR,
      isPackaged: false,
    }
  }

  const uvBinName = process.platform === 'win32' ? 'uv.exe' : 'uv'
  return {
    uvBin: join(process.resourcesPath, 'uv', uvBinName),
    projectDir: join(app.getPath('userData'), 'backend'),
    isPackaged: true,
  }
}

/** Solo en empaquetado: carpeta de recursos bundleados con el código fuente del backend (solo lectura). */
export function bundledBackendSourceDir(): string {
  return join(process.resourcesPath, 'backend')
}
