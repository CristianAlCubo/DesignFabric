/**
 * Handlers IPC del wizard de primer arranque (Fase 3).
 *
 * El renderer (Fase 5, fuera del alcance de este archivo) consulta
 * `setup:get-preferences` para saber si debe mostrar el wizard, y llama
 * `setup:complete-wizard` cuando el usuario termina de elegir. Si el usuario
 * difirió la instalación de IA local, más tarde puede pedirla vía
 * `setup:install-local-ai-later`.
 */

import { app, ipcMain } from 'electron'

import { killBackend, spawnBackend, waitForBackendReady } from './backend-process'
import { pushLog } from './log-store'
import { syncExtra } from './pythonSetup'
import { readSetupPreferences, writeSetupPreferences } from './setup-preferences'
import type { LocalAiChoice, SetupPreferences } from '@shared/setupPreferences'

// Timeout generoso: `uv sync` de torch/diffusers puede tardar varios minutos.
const BACKEND_READY_TIMEOUT_MS = 15 * 60 * 1000

// En dev, `bootstrap()` (index.ts) nunca gatea por el wizard: arranca el
// backend directo, siempre. El renderer, sin embargo, siempre consulta este
// canal al montar — si devolviéramos el archivo de preferencias real (que
// nunca se escribe en dev), el wizard aparecería igual, contradiciendo el
// requisito de que dev no cambie de comportamiento visible. Por eso, en dev
// reportamos siempre "wizard completado + IA instalada" sin tocar disco.
export function registerSetupIpc(): void {
  ipcMain.handle('setup:get-preferences', (): SetupPreferences =>
    app.isPackaged ? readSetupPreferences() : { wizardCompleted: true, localAiChoice: 'installed', version: 1 }
  )

  // Se dispara cuando el usuario termina el wizard (elija o no instalar IA
  // local). Persiste la elección y recién ahí arranca el backend (en
  // empaquetado, `bootstrap()` no lo arrancó de entrada precisamente para
  // esperar esta llamada).
  ipcMain.handle('setup:complete-wizard', async (_event, choice: LocalAiChoice): Promise<SetupPreferences> => {
    const prefs: SetupPreferences = { wizardCompleted: true, localAiChoice: choice, version: 1 }
    writeSetupPreferences(prefs)

    const extras = choice === 'installed' ? ['local-ai'] : []
    try {
      await spawnBackend(extras)
      await waitForBackendReady(BACKEND_READY_TIMEOUT_MS)
    } catch (err) {
      pushLog({ source: 'main', stream: 'error', line: `Error al iniciar el backend tras el wizard: ${String(err)}` })
      throw err
    }
    return prefs
  })

  // Caso "instalar más tarde": el backend ya está corriendo sin el extra
  // `local-ai`. Hay que matarlo, sincronizar el extra sobre el venv
  // existente (sin recopiar el proyecto) y volver a arrancarlo.
  ipcMain.handle('setup:install-local-ai-later', async (): Promise<void> => {
    killBackend()
    const current = readSetupPreferences()
    writeSetupPreferences({ ...current, wizardCompleted: true, localAiChoice: 'installed' })

    try {
      await syncExtra('local-ai')
      await spawnBackend(['local-ai'])
      await waitForBackendReady(BACKEND_READY_TIMEOUT_MS)
    } catch (err) {
      pushLog({ source: 'main', stream: 'error', line: `Error al instalar el módulo de IA local: ${String(err)}` })
      throw err
    }
  })
}
