/**
 * IPC de configuración de rutas a modelos ONNX locales.
 */

import { ipcMain } from 'electron'

import type { ModelPathPreferences } from '@shared/modelPathPreferences'

import {
  readModelPathPreferences,
  writeModelPathPreferences
} from './model-path-preferences'
import { syncModelPathsToBackend } from './model-path-sync'

export function registerModelPathSettingsIpc(): void {
  ipcMain.handle('settings:getModelPaths', (): ModelPathPreferences => {
    return readModelPathPreferences()
  })

  ipcMain.handle(
    'settings:setModelPaths',
    async (_event, prefs: ModelPathPreferences): Promise<ModelPathPreferences> => {
      writeModelPathPreferences(prefs)
      await syncModelPathsToBackend()
      return readModelPathPreferences()
    }
  )
}
