import { readdir, readFile, writeFile } from 'node:fs/promises'
import { extname, join } from 'node:path'

import { app, BrowserWindow, dialog, ipcMain, Menu, shell } from 'electron'

import { killBackend, spawnBackend, waitForBackendReady } from './backend-process'
import { backendBaseUrl } from './config'
import { readAppVersion } from './app-version'
import { getLastImageDirectory, rememberImageDirectory } from './lastImageDirectory'
import { getLogHistory, pushLog } from './log-store'
import { registerSetupIpc } from './setup-ipc'
import { readSetupPreferences } from './setup-preferences'
import { createMainWindow } from './window'

// Workaround de renderizado en Linux (mismo que ClearCut original): evita problemas de
// GTK4 con algunas distros. Debe aplicarse ANTES de `app.whenReady()`.
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('gtk-version', '3')
}

const IMAGE_FILTERS = [{ name: 'Imágenes', extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp'] }]

/** Extensiones que el pipeline ClearCut acepta (alineado a `SUPPORTED_EXTENSIONS` del backend). */
const BATCH_IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp'])

const MIME_BY_EXT: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.bmp': 'image/bmp'
}

ipcMain.handle('get-backend-base-url', (): string => backendBaseUrl)

ipcMain.handle('app:get-version', (): string => readAppVersion())

ipcMain.handle('get-log-history', () => getLogHistory())

ipcMain.handle('dialog:openImage', async (): Promise<string | undefined> => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile'],
    defaultPath: getLastImageDirectory(),
    filters: IMAGE_FILTERS,
  })
  if (result.canceled || result.filePaths.length === 0) return undefined
  const [filePath] = result.filePaths
  rememberImageDirectory(filePath)
  return filePath
})

ipcMain.handle('dialog:openImages', async (): Promise<string[]> => {
  const result = await dialog.showOpenDialog({
    properties: ['openFile', 'multiSelections'],
    defaultPath: getLastImageDirectory(),
    filters: IMAGE_FILTERS,
  })
  if (result.canceled || result.filePaths.length === 0) return []
  rememberImageDirectory(result.filePaths[0])
  return result.filePaths
})

ipcMain.handle('dialog:openDirectory', async (): Promise<string | undefined> => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    defaultPath: getLastImageDirectory(),
  })
  if (result.canceled || result.filePaths.length === 0) return undefined
  const [directoryPath] = result.filePaths
  // `rememberImageDirectory` deriva el directorio con `dirname(imagePath)`; le pasamos
  // una ruta ficticia *dentro* del directorio elegido para que lo recuerde tal cual.
  rememberImageDirectory(join(directoryPath, '.placeholder'))
  return directoryPath
})

/** Cuenta imágenes soportadas en una carpeta (sin subcarpetas), para preflight del lote. */
ipcMain.handle('fs:countImagesInDirectory', async (_event, directoryPath: string): Promise<number> => {
  const entries = await readdir(directoryPath, { withFileTypes: true })
  return entries.filter(
    (entry) => entry.isFile() && BATCH_IMAGE_EXTENSIONS.has(extname(entry.name).toLowerCase())
  ).length
})

// Convierte una imagen local en disco a data URL — el CSP del renderer no
// permite `file://`, así que las previews de imágenes elegidas con el
// diálogo nativo se cargan como data URL en vez de por ruta directa.
ipcMain.handle('image:preview', async (_event, filePath: string): Promise<string> => {
  const ext = extname(filePath).toLowerCase()
  const mime = MIME_BY_EXT[ext] ?? 'application/octet-stream'
  const buffer = await readFile(filePath)
  return `data:${mime};base64,${buffer.toString('base64')}`
})

// Exporta el resultado de una feature (servido por el backend en una URL
// local, ej. `http://127.0.0.1:PORT/output/...`) a una ruta elegida por el
// usuario vía diálogo nativo de guardado.
ipcMain.handle(
  'image:export',
  async (_event, payload: { sourceUrl: string; suggestedName: string }): Promise<string | undefined> => {
    const result = await dialog.showSaveDialog({
      defaultPath: join(getLastImageDirectory() ?? app.getPath('pictures'), payload.suggestedName),
      filters: IMAGE_FILTERS
    })
    if (result.canceled || !result.filePath) return undefined

    const response = await fetch(payload.sourceUrl)
    if (!response.ok) {
      throw new Error(`No se pudo leer la imagen a exportar (${response.status}).`)
    }
    const buffer = Buffer.from(await response.arrayBuffer())
    await writeFile(result.filePath, buffer)
    rememberImageDirectory(result.filePath)
    return result.filePath
  }
)

// Abre una ruta (archivo o carpeta) en el explorador de archivos del SO.
ipcMain.handle('shell:openPath', async (_event, targetPath: string): Promise<string> => {
  return shell.openPath(targetPath)
})

function startBackendInBackground(extras: string[]): void {
  // `spawnBackend` es async (en empaquetado, primero asegura el entorno
  // Python en `userData` — puede tardar varios minutos en el primer
  // arranque). No se espera aquí para no bloquear la ventana: se deja
  // correr en segundo plano, igual que ya hacía `waitForBackendReady`.
  void spawnBackend(extras).catch((err: unknown) => {
    const line = `Failed to start backend: ${String(err)}`
    console.error(line)
    pushLog({ source: 'main', stream: 'error', line })
  })

  // Timeout generoso: en el primer arranque de una build empaquetada, `uv
  // sync` (torch/diffusers/etc.) puede tardar varios minutos y ocurre antes
  // de que uvicorn siquiera empiece a escuchar.
  waitForBackendReady(15 * 60 * 1000).catch((err: unknown) => {
    const line = `Backend did not become ready in time: ${String(err)}`
    console.error(line)
    pushLog({ source: 'main', stream: 'error', line })
  })
}

function bootstrap(): void {
  registerSetupIpc()

  if (!app.isPackaged) {
    // Dev: comportamiento idéntico a siempre, sin wizard de por medio (el
    // desarrollador ya corrió `uv sync --extra dev` a mano).
    startBackendInBackground([])
    createMainWindow()
    return
  }

  const prefs = readSetupPreferences()
  if (!prefs.wizardCompleted) {
    // Primer arranque empaquetado sin preferencias todavía: NO arrancamos el
    // backend aquí. El renderer (Fase 5) mostrará el wizard de bienvenida y,
    // cuando el usuario responda, el handler `setup:complete-wizard` (ver
    // `setup-ipc.ts`) es quien dispara `spawnBackend` con los extras
    // correctos.
    createMainWindow()
    return
  }

  const extras = prefs.localAiChoice === 'installed' ? ['local-ai'] : []
  startBackendInBackground(extras)
  createMainWindow()
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null)
  bootstrap()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  killBackend()
})
