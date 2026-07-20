/**
 * IPC de configuración OpenRouter / preferencias de generación.
 */

import { ipcMain } from 'electron'

import type {
  GenerationPreferences,
  OpenRouterPublicStatus
} from '@shared/generationPreferences'

import {
  readGenerationPreferences,
  writeGenerationPreferences
} from './generation-preferences'
import {
  clearOpenRouterApiKey,
  isOpenRouterEncryptionAvailable,
  maskApiKey,
  readOpenRouterApiKey,
  writeOpenRouterApiKey
} from './openrouter-secrets'
import { syncOpenRouterToBackend } from './openrouter-sync'

export function registerOpenRouterSettingsIpc(): void {
  ipcMain.handle('settings:getOpenRouter', (): OpenRouterPublicStatus => {
    const key = readOpenRouterApiKey()
    return {
      configured: Boolean(key),
      maskedKey: maskApiKey(key),
      encryptionAvailable: isOpenRouterEncryptionAvailable()
    }
  })

  ipcMain.handle('settings:setOpenRouterKey', async (_event, apiKey: string): Promise<OpenRouterPublicStatus> => {
    writeOpenRouterApiKey(apiKey)
    await syncOpenRouterToBackend()
    const key = readOpenRouterApiKey()
    return {
      configured: Boolean(key),
      maskedKey: maskApiKey(key),
      encryptionAvailable: isOpenRouterEncryptionAvailable()
    }
  })

  ipcMain.handle('settings:clearOpenRouterKey', async (): Promise<OpenRouterPublicStatus> => {
    clearOpenRouterApiKey()
    await syncOpenRouterToBackend()
    return {
      configured: false,
      maskedKey: null,
      encryptionAvailable: isOpenRouterEncryptionAvailable()
    }
  })

  ipcMain.handle('settings:getGenerationPreferences', (): GenerationPreferences => {
    return readGenerationPreferences()
  })

  ipcMain.handle(
    'settings:setGenerationPreferences',
    async (_event, prefs: GenerationPreferences): Promise<GenerationPreferences> => {
      writeGenerationPreferences(prefs)
      await syncOpenRouterToBackend()
      return readGenerationPreferences()
    }
  )
}
