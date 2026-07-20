import { type ChildProcessByStdio, spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import type { Readable } from 'node:stream'

import { backendBaseUrl, backendPort } from './config'
import { pushLog } from './log-store'
import { ensurePythonEnvironment } from './pythonSetup'
import { resolveBackendRuntime } from './runtime'

let backendProcess: ChildProcessByStdio<null, Readable, Readable> | null = null

/**
 * Lanza el backend FastAPI (`uv run uvicorn designfabricv2.api.app:app`) como
 * proceso hijo.
 *
 * En dev usa el `uv` del PATH y el `backend/` del propio repo (sin cambios de
 * comportamiento). En empaquetado, primero asegura el entorno Python de
 * `userData` (copia de fuentes + `uv sync`, solo la primera vez o tras una
 * actualización — ver `pythonSetup.ts`) y luego lanza uvicorn con el `uv`
 * bundleado sobre ese proyecto copiado.
 *
 * `extras` son los extras opcionales de `pyproject.toml` a asegurar antes de
 * arrancar (hoy, como mucho: `['local-ai']`) — se reenvían tal cual a
 * `ensurePythonEnvironment`. En dev se ignoran (no-op ahí).
 */
export async function spawnBackend(extras: string[] = []): Promise<void> {
  if (backendProcess) return

  await ensurePythonEnvironment(extras)

  const runtime = resolveBackendRuntime()

  const child = spawn(
    runtime.uvBin,
    ['run', 'uvicorn', 'designfabricv2.api.app:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    {
      cwd: runtime.projectDir,
      env: { ...process.env, DESIGNFABRIC_API_PORT: String(backendPort) },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  )
  backendProcess = child

  createInterface({ input: child.stdout }).on('line', (line) => {
    console.log(`[backend] ${line}`)
    pushLog({ source: 'backend', stream: 'stdout', line })
  })

  createInterface({ input: child.stderr }).on('line', (line) => {
    console.error(`[backend] ${line}`)
    pushLog({ source: 'backend', stream: 'stderr', line })
  })

  child.on('exit', (code, signal) => {
    const line = `Backend process exited (code=${code ?? 'null'}, signal=${signal ?? 'null'})`
    console.error(`[backend] ${line}`)
    pushLog({ source: 'main', stream: 'error', line })
    backendProcess = null
  })

  child.on('error', (err) => {
    const line = `Failed to spawn backend process: ${String(err)}`
    console.error(`[backend] ${line}`)
    pushLog({ source: 'main', stream: 'error', line })
  })
}

/** Mata el proceso backend, si está corriendo. Usado en `before-quit`. */
export function killBackend(): void {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill()
  }
  backendProcess = null
}

/** Espera (polling) hasta que `GET {backendBaseUrl}/health` responda OK, o hasta agotar `timeoutMs`. */
export async function waitForBackendReady(timeoutMs = 30000): Promise<void> {
  const start = Date.now()
  const pollIntervalMs = 300

  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(`${backendBaseUrl}/health`)
      if (response.ok) return
    } catch {
      // El backend todavía no está escuchando; reintentar.
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs))
  }

  throw new Error(`Backend did not become ready within ${timeoutMs}ms`)
}
