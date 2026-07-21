/**
 * Preferencias de rutas a modelos ONNX en userData.
 */

import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { app } from 'electron'

import {
  DEFAULT_MODEL_PATH_PREFERENCES,
  type ModelPathPreferences
} from '@shared/modelPathPreferences'

function prefsPath(): string {
  return join(app.getPath('userData'), 'model-path-preferences.json')
}

function normalizePath(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

export function readModelPathPreferences(): ModelPathPreferences {
  try {
    const target = prefsPath()
    if (!existsSync(target)) return { ...DEFAULT_MODEL_PATH_PREFERENCES }
    const raw = readFileSync(target, 'utf-8')
    const parsed = JSON.parse(raw) as {
      version?: number
      sam2OnnxPath?: string | null
      sam2EncoderOnnxPath?: string | null
      sam2DecoderOnnxPath?: string | null
      vitMatteOnnxPath?: string | null
      isnetGeneralOnnxPath?: string | null
    }

    const encoder =
      normalizePath(parsed.sam2EncoderOnnxPath) ?? normalizePath(parsed.sam2OnnxPath)
    const decoder = normalizePath(parsed.sam2DecoderOnnxPath)

    return {
      version: 3,
      sam2EncoderOnnxPath: encoder,
      sam2DecoderOnnxPath: decoder,
      vitMatteOnnxPath: normalizePath(parsed.vitMatteOnnxPath),
      isnetGeneralOnnxPath: normalizePath(parsed.isnetGeneralOnnxPath)
    }
  } catch {
    return { ...DEFAULT_MODEL_PATH_PREFERENCES }
  }
}

export function writeModelPathPreferences(prefs: ModelPathPreferences): void {
  const target = prefsPath()
  const tmp = `${target}.tmp`
  const payload: ModelPathPreferences = {
    version: 3,
    sam2EncoderOnnxPath: normalizePath(prefs.sam2EncoderOnnxPath),
    sam2DecoderOnnxPath: normalizePath(prefs.sam2DecoderOnnxPath),
    vitMatteOnnxPath: normalizePath(prefs.vitMatteOnnxPath),
    isnetGeneralOnnxPath: normalizePath(prefs.isnetGeneralOnnxPath)
  }
  writeFileSync(tmp, JSON.stringify(payload, null, 2))
  renameSync(tmp, target)
}
