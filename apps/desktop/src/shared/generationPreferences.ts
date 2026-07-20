/**
 * Preferencias de generación (no secretos).
 * La API key de OpenRouter vive cifrada aparte vía safeStorage.
 */

export interface OpenRouterModelPreferences {
  textModelId: string | null
  imageModelId: string | null
  /** Capacidades de salida del modelo de imagen (catálogo OpenRouter). */
  imageModelOutputModalities: string[] | null
  /** El modelo de imagen seleccionado declara background=transparent. */
  imageModelSupportsTransparency: boolean
}

export interface GenerationPreferences {
  version: 2
  openrouter: OpenRouterModelPreferences
}

export const DEFAULT_GENERATION_PREFERENCES: GenerationPreferences = {
  version: 2,
  openrouter: {
    textModelId: null,
    imageModelId: null,
    imageModelOutputModalities: null,
    imageModelSupportsTransparency: false
  }
}

/** Vista pública de OpenRouter para la UI (sin key completa). */
export interface OpenRouterPublicStatus {
  configured: boolean
  maskedKey: string | null
  encryptionAvailable: boolean
}
