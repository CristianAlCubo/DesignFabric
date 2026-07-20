/**
 * Preferencias de generación (modelos OpenRouter, etc.) en userData.
 */

import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { app } from 'electron'

import {
  DEFAULT_GENERATION_PREFERENCES,
  type GenerationPreferences
} from '@shared/generationPreferences'

function prefsPath(): string {
  return join(app.getPath('userData'), 'generation-preferences.json')
}

export function readGenerationPreferences(): GenerationPreferences {
  try {
    const target = prefsPath()
    if (!existsSync(target)) return { ...DEFAULT_GENERATION_PREFERENCES }
    const raw = readFileSync(target, 'utf-8')
    const parsed = JSON.parse(raw) as Partial<GenerationPreferences>
    return {
      version: 1,
      openrouter: {
        textModelId: parsed.openrouter?.textModelId ?? null,
        imageModelId: parsed.openrouter?.imageModelId ?? null
      }
    }
  } catch {
    return { ...DEFAULT_GENERATION_PREFERENCES }
  }
}

export function writeGenerationPreferences(prefs: GenerationPreferences): void {
  const target = prefsPath()
  const tmp = `${target}.tmp`
  const payload: GenerationPreferences = {
    version: 1,
    openrouter: {
      textModelId: prefs.openrouter.textModelId,
      imageModelId: prefs.openrouter.imageModelId
    }
  }
  writeFileSync(tmp, JSON.stringify(payload, null, 2))
  renameSync(tmp, target)
}
