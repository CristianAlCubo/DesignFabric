/**
 * Preferencias de generación (no secretos).
 * La API key de OpenRouter vive cifrada aparte vía safeStorage.
 */

export interface OpenRouterModelPreferences {
  textModelId: string | null
  imageModelId: string | null
}

export interface GenerationPreferences {
  version: 1
  openrouter: OpenRouterModelPreferences
}

export const DEFAULT_GENERATION_PREFERENCES: GenerationPreferences = {
  version: 1,
  openrouter: {
    textModelId: null,
    imageModelId: null
  }
}

/** Vista pública de OpenRouter para la UI (sin key completa). */
export interface OpenRouterPublicStatus {
  configured: boolean
  maskedKey: string | null
  encryptionAvailable: boolean
}
