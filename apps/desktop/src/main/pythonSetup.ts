/**
 * Bootstrap de "primer arranque" del entorno Python en builds empaquetadas.
 *
 * El instalador (`.exe`/`.AppImage`) es liviano: solo trae Electron + el
 * binario `uv` bundleado + el CÓDIGO FUENTE del backend (`backend/src`,
 * `pyproject.toml`, `uv.lock`), sin las dependencias Python instaladas
 * (torch/diffusers/transformers pesan varios GB y PyInstaller+CUDA es
 * frágil — ver decisión de arquitectura acordada). En el primer arranque:
 *
 *   1. Se copia el código fuente bundleado (solo lectura) a una carpeta
 *      escribible en `userData/backend`.
 *   2. Se corre `uv sync` ahí dentro, lo que descarga e instala TODAS las
 *      dependencias desde PyPI — puede tardar varios minutos y requiere
 *      internet. Ocurre una sola vez; se cachea para siempre.
 *   3. Se re-corre solo si la versión de la app cambió desde la última vez
 *      (marcador `.ready-version` en el proyecto copiado).
 *
 * En DESARROLLO (`app.isPackaged === false`) esta función es un no-op: el
 * flujo de `npm run dev` sigue exactamente igual que hoy (uv del sistema +
 * `backend/` del repo, ya sincronizado a mano por el desarrollador).
 *
 * Todo el progreso se reporta vía `pushLog` para que se vea en vivo en el
 * `LogConsole` de la propia app.
 */

import { existsSync } from 'node:fs'
import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import { join } from 'node:path'
import { app } from 'electron'

import { bundledBackendSourceDir, resolveBackendRuntime } from './runtime'
import { pushLog } from './log-store'

const READY_MARKER = '.ready-version'

function currentAppVersion(): string {
  return app.getVersion()
}

async function readMarker(projectDir: string): Promise<string | null> {
  try {
    return (await readFile(join(projectDir, READY_MARKER), 'utf-8')).trim()
  } catch {
    return null
  }
}

function runCommand(command: string, args: string[], cwd: string, label: string): Promise<void> {
  return new Promise((resolve, reject) => {
    pushLog({ source: 'main', stream: 'info', line: `${label}: ${command} ${args.join(' ')}` })
    const child = spawn(command, args, { cwd, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] })

    createInterface({ input: child.stdout }).on('line', (line) =>
      pushLog({ source: 'main', stream: 'stdout', line: `[${label}] ${line}` }),
    )
    createInterface({ input: child.stderr }).on('line', (line) =>
      pushLog({ source: 'main', stream: 'stderr', line: `[${label}] ${line}` }),
    )

    child.on('error', (err) => reject(err))
    child.on('exit', (code) => {
      if (code === 0) resolve()
      else reject(new Error(`${label} terminó con código ${code}`))
    })
  })
}

/**
 * En empaquetado: si el proyecto Python en `userData` no existe, quedó de
 * una versión distinta de la app, o los extras instalados no coinciden con
 * los pedidos, lo (re)copia desde los recursos bundleados y corre `uv sync`
 * (descarga las dependencias — puede tardar varios minutos la primera vez,
 * requiere internet). En dev, no hace nada (no-op).
 *
 * `extras` son los extras opcionales de `pyproject.toml` a instalar además
 * de las dependencias base (hoy, como mucho: `['local-ai']`). El marcador
 * `.ready-version` codifica versión de la app + extras instalados
 * (`"1.2.3|local-ai"`) para poder detectar cuándo hace falta re-sincronizar
 * porque el usuario decidió instalar el módulo de IA local después de todo.
 */
export async function ensurePythonEnvironment(extras: string[] = []): Promise<void> {
  const runtime = resolveBackendRuntime()
  if (!runtime.isPackaged) return // dev: el desarrollador ya corrió `uv sync --extra dev` a mano

  const extrasKey = [...extras].sort().join(',')
  const marker = await readMarker(runtime.projectDir)
  const expected = `${currentAppVersion()}|${extrasKey}`
  if (marker === expected && existsSync(join(runtime.projectDir, '.venv'))) {
    pushLog({
      source: 'main',
      stream: 'info',
      line: `Entorno Python ya configurado (versión ${currentAppVersion()}, extras: ${extrasKey || 'ninguno'}).`,
    })
    return
  }

  pushLog({
    source: 'main',
    stream: 'info',
    line:
      'Configurando el entorno de IA por primera vez (o tras una actualización) — ' +
      'esto puede tardar varios minutos y requiere conexión a internet…',
  })

  await rm(runtime.projectDir, { recursive: true, force: true })
  await mkdir(runtime.projectDir, { recursive: true })
  await cp(bundledBackendSourceDir(), runtime.projectDir, { recursive: true })

  const args = extras.length ? ['sync', ...extras.flatMap((extra) => ['--extra', extra])] : ['sync']
  await runCommand(runtime.uvBin, args, runtime.projectDir, 'uv sync')

  await writeFile(join(runtime.projectDir, READY_MARKER), expected, 'utf-8')
  pushLog({ source: 'main', stream: 'info', line: 'Entorno Python listo.' })
}

/**
 * Instala un extra adicional (hoy: `'local-ai'`) sobre un entorno Python ya
 * existente en `userData/backend`, SIN borrar ni recopiar el código fuente
 * (que ya está ahí y no cambió). Pensado para el caso "el usuario difirió
 * la instalación de IA local en el wizard y la pide más tarde desde la UI".
 *
 * No-op en dev (no debería llamarse ahí, pero por robustez se ignora igual
 * que `ensurePythonEnvironment`).
 */
export async function syncExtra(extra: string): Promise<void> {
  const runtime = resolveBackendRuntime()
  if (!runtime.isPackaged) return

  pushLog({ source: 'main', stream: 'info', line: `Instalando el módulo "${extra}" (esto puede tardar varios minutos)…` })
  await runCommand(runtime.uvBin, ['sync', '--extra', extra], runtime.projectDir, 'uv sync')

  const marker = await readMarker(runtime.projectDir)
  const currentExtras = marker?.split('|')[1]?.split(',').filter(Boolean) ?? []
  const nextExtras = [...new Set([...currentExtras, extra])].sort().join(',')
  await writeFile(join(runtime.projectDir, READY_MARKER), `${currentAppVersion()}|${nextExtras}`, 'utf-8')
  pushLog({ source: 'main', stream: 'info', line: `Módulo "${extra}" instalado.` })
}
