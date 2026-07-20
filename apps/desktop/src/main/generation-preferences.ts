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

function normalizeModalities(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null
  const cleaned = value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
  return cleaned.length > 0 ? cleaned : null
}

export function readGenerationPreferences(): GenerationPreferences {
  try {
    const target = prefsPath()
    if (!existsSync(target)) return { ...DEFAULT_GENERATION_PREFERENCES }
    const raw = readFileSync(target, 'utf-8')
    const parsed = JSON.parse(raw) as {
      openrouter?: {
        textModelId?: string | null
        imageModelId?: string | null
        imageModelOutputModalities?: string[] | null
      }
    }
    return {
      version: 2,
      openrouter: {
        textModelId: parsed.openrouter?.textModelId ?? null,
        imageModelId: parsed.openrouter?.imageModelId ?? null,
        imageModelOutputModalities: normalizeModalities(
          parsed.openrouter?.imageModelOutputModalities
        )
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
    version: 2,
    openrouter: {
      textModelId: prefs.openrouter.textModelId,
      imageModelId: prefs.openrouter.imageModelId,
      imageModelOutputModalities: normalizeModalities(
        prefs.openrouter.imageModelOutputModalities
      )
    }
  }
  writeFileSync(tmp, JSON.stringify(payload, null, 2))
  renameSync(tmp, target)
}
