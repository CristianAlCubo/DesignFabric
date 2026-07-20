/**
 * Sincroniza key + modelos OpenRouter al backend (runtime config).
 */

import { backendBaseUrl } from './config'
import { pushLog } from './log-store'
import { readGenerationPreferences } from './generation-preferences'
import { readOpenRouterApiKey } from './openrouter-secrets'

export async function syncOpenRouterToBackend(): Promise<void> {
  const apiKey = readOpenRouterApiKey()
  const prefs = readGenerationPreferences()

  const body: Record<string, unknown> = {
    text_model_id: prefs.openrouter.textModelId,
    image_model_id: prefs.openrouter.imageModelId
  }

  if (apiKey) {
    body.api_key = apiKey
  } else {
    body.clear_api_key = true
  }

  if (!prefs.openrouter.textModelId) body.clear_text_model = true
  if (!prefs.openrouter.imageModelId) body.clear_image_model = true

  try {
    const response = await fetch(`${backendBaseUrl}/api/settings/openrouter`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!response.ok) {
      const detail = await response.text()
      pushLog({
        source: 'main',
        stream: 'error',
        line: `OpenRouter sync failed (${response.status}): ${detail}`
      })
    }
  } catch (err) {
    pushLog({
      source: 'main',
      stream: 'error',
      line: `OpenRouter sync error: ${String(err)}`
    })
  }
}

/** Env bootstrap para el spawn del backend (antes del PUT). */
export function openRouterEnvBootstrap(): Record<string, string> {
  const env: Record<string, string> = {}
  const apiKey = readOpenRouterApiKey()
  const prefs = readGenerationPreferences()
  if (apiKey) env.DESIGNFABRIC_OPENROUTER_API_KEY = apiKey
  if (prefs.openrouter.textModelId) {
    env.DESIGNFABRIC_OPENROUTER_TEXT_MODEL = prefs.openrouter.textModelId
  }
  if (prefs.openrouter.imageModelId) {
    env.DESIGNFABRIC_OPENROUTER_IMAGE_MODEL = prefs.openrouter.imageModelId
  }
  return env
}
