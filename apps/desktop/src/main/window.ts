import { join } from 'node:path'

import { BrowserWindow } from 'electron'

const WEB_PREFERENCES: Electron.WebPreferences = {
  preload: join(__dirname, '../preload/index.js'),
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: false,
}

let settingsWindow: BrowserWindow | null = null

function loadRendererPage(window: BrowserWindow, page: 'index.html' | 'settings.html'): void {
  if (process.env.ELECTRON_RENDERER_URL) {
    const base = process.env.ELECTRON_RENDERER_URL.replace(/\/$/, '')
    window.loadURL(page === 'index.html' ? base : `${base}/${page}`)
  } else {
    window.loadFile(join(__dirname, `../renderer/${page}`))
  }
}

/**
 * Crea la ventana principal: SIEMPRE maximizada (toda la pantalla) pero
 * conservando la topbar nativa del sistema operativo (título + botones
 * minimizar/maximizar/cerrar). Solo se oculta la barra de menú propia de
 * Electron (File/Edit/View/...), NUNCA `frame: false`/`fullscreen`/`kiosk`,
 * que ocultarían también los controles nativos del SO.
 */
export function createMainWindow(): BrowserWindow {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 560,
    show: false,
    title: 'DesignFabric',
    autoHideMenuBar: true,
    webPreferences: WEB_PREFERENCES,
  })

  mainWindow.setMenuBarVisibility(false)

  mainWindow.on('ready-to-show', () => {
    mainWindow.maximize()
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  loadRendererPage(mainWindow, 'index.html')

  return mainWindow
}

/**
 * Abre (o enfoca) la ventana hija de configuración. Singleton: una sola
 * instancia; si ya existe, se trae al frente en lugar de crear otra.
 */
export function openSettingsWindow(parent?: BrowserWindow | null): void {
  if (settingsWindow && !settingsWindow.isDestroyed()) {
    if (settingsWindow.isMinimized()) settingsWindow.restore()
    settingsWindow.focus()
    return
  }

  settingsWindow = new BrowserWindow({
    width: 860,
    height: 600,
    minWidth: 640,
    minHeight: 420,
    show: false,
    title: 'Configuración',
    parent: parent && !parent.isDestroyed() ? parent : undefined,
    autoHideMenuBar: true,
    webPreferences: WEB_PREFERENCES,
  })

  settingsWindow.setMenuBarVisibility(false)

  settingsWindow.on('ready-to-show', () => {
    settingsWindow?.show()
  })

  settingsWindow.on('closed', () => {
    settingsWindow = null
  })

  settingsWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  loadRendererPage(settingsWindow, 'settings.html')
}
