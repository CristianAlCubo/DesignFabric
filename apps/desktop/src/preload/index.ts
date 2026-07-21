import { contextBridge, ipcRenderer } from 'electron'

import type { LogEntry } from '@shared/logEntry'
import type {
  GenerationPreferences,
  OpenRouterPublicStatus
} from '@shared/generationPreferences'
import type { ModelPathPreferences } from '@shared/modelPathPreferences'

const api = {
  getBackendBaseUrl: (): Promise<string> => ipcRenderer.invoke('get-backend-base-url'),

  getAppVersion: (): Promise<string> => ipcRenderer.invoke('app:get-version'),

  getLogHistory: (): Promise<LogEntry[]> => ipcRenderer.invoke('get-log-history'),

  onLog: (callback: (entry: LogEntry) => void): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, entry: LogEntry): void => callback(entry)
    ipcRenderer.on('app-log', listener)
    return () => ipcRenderer.removeListener('app-log', listener)
  },

  openImageDialog: (): Promise<string | undefined> => ipcRenderer.invoke('dialog:openImage'),

  openImagesDialog: (): Promise<string[]> => ipcRenderer.invoke('dialog:openImages'),

  openDirectoryDialog: (): Promise<string | undefined> => ipcRenderer.invoke('dialog:openDirectory'),

  openOnnxFileDialog: (): Promise<string | undefined> => ipcRenderer.invoke('dialog:openOnnxFile'),

  /** Cuenta imágenes soportadas (png/jpg/jpeg/webp) en una carpeta, sin subcarpetas. */
  countImagesInDirectory: (directoryPath: string): Promise<number> =>
    ipcRenderer.invoke('fs:countImagesInDirectory', directoryPath),

  /** Convierte una imagen local en disco a data URL (el CSP no permite `file://`). */
  getImagePreview: (filePath: string): Promise<string> => ipcRenderer.invoke('image:preview', filePath),

  /** Guarda una imagen servida por el backend en una ruta elegida por el usuario. */
  exportImage: (sourceUrl: string, suggestedName: string): Promise<string | undefined> =>
    ipcRenderer.invoke('image:export', { sourceUrl, suggestedName }),

  /** Abre una ruta (archivo o carpeta) en el explorador de archivos del SO. */
  openPath: (targetPath: string): Promise<string> => ipcRenderer.invoke('shell:openPath', targetPath),

  /** Instala el módulo de IA local: reinicia el backend con el extra `local-ai`. */
  installLocalAiLater: (): Promise<void> => ipcRenderer.invoke('setup:install-local-ai-later'),

  /** Abre (o enfoca) la ventana hija de configuración. */
  openSettings: (): Promise<void> => ipcRenderer.invoke('settings:open'),

  getOpenRouterStatus: (): Promise<OpenRouterPublicStatus> =>
    ipcRenderer.invoke('settings:getOpenRouter'),

  setOpenRouterKey: (apiKey: string): Promise<OpenRouterPublicStatus> =>
    ipcRenderer.invoke('settings:setOpenRouterKey', apiKey),

  clearOpenRouterKey: (): Promise<OpenRouterPublicStatus> =>
    ipcRenderer.invoke('settings:clearOpenRouterKey'),

  getGenerationPreferences: (): Promise<GenerationPreferences> =>
    ipcRenderer.invoke('settings:getGenerationPreferences'),

  setGenerationPreferences: (prefs: GenerationPreferences): Promise<GenerationPreferences> =>
    ipcRenderer.invoke('settings:setGenerationPreferences', prefs),

  getModelPaths: (): Promise<ModelPathPreferences> => ipcRenderer.invoke('settings:getModelPaths'),

  setModelPaths: (prefs: ModelPathPreferences): Promise<ModelPathPreferences> =>
    ipcRenderer.invoke('settings:setModelPaths', prefs)
}

contextBridge.exposeInMainWorld('designfabric', api)

export type DesignFabricApi = typeof api
