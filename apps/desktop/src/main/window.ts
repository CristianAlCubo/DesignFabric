import { join } from 'node:path'

import { BrowserWindow } from 'electron'

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
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  mainWindow.setMenuBarVisibility(false)

  mainWindow.on('ready-to-show', () => {
    mainWindow.maximize()
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return mainWindow
}
