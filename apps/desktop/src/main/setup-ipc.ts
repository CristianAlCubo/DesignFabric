/**
 * Handler IPC para instalar el módulo de IA local (extra `local-ai`) desde
 * Settings, en cualquier momento después del primer arranque.
 */

import { ipcMain } from 'electron'

import { killBackend, spawnBackend, waitForBackendReady } from './backend-process'
import { pushLog } from './log-store'
import { syncExtra } from './pythonSetup'
import { readSetupPreferences, writeSetupPreferences } from './setup-preferences'

// Timeout generoso: `uv sync` de torch/diffusers puede tardar varios minutos.
const BACKEND_READY_TIMEOUT_MS = 15 * 60 * 1000

export function registerSetupIpc(): void {
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
