/**
 * Presets de exportación multi-tamaño en userData: JSON versionado, escritura atómica
 * (mismo patrón que `model-path-preferences.ts`). Solo se persisten presets de usuario;
 * los de fábrica (`BUILTIN_MULTI_EXPORT_PRESETS`) se mezclan en memoria al listar y nunca
 * tocan disco, así que agregar/ajustar built-ins no requiere migración de datos.
 */

import { randomUUID } from 'node:crypto'
import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { app } from 'electron'

import {
  BUILTIN_MULTI_EXPORT_PRESETS,
  DEFAULT_MULTI_EXPORT_PRESETS_FILE,
  type MultiExportPreset,
  type MultiExportPresetsFile,
  type SizeRow
} from '@shared/multiExportPresets'

export class BuiltinPresetImmutableError extends Error {
  constructor(id: string) {
    super(`El preset "${id}" es de fábrica y no se puede editar ni eliminar.`)
    this.name = 'BuiltinPresetImmutableError'
  }
}

export class PresetNotFoundError extends Error {
  constructor(id: string) {
    super(`No existe el preset "${id}".`)
    this.name = 'PresetNotFoundError'
  }
}

function storePath(): string {
  return join(app.getPath('userData'), 'multi-export-presets.json')
}

function readUserPresets(): MultiExportPreset[] {
  try {
    const target = storePath()
    if (!existsSync(target)) return []
    const raw = readFileSync(target, 'utf-8')
    const parsed = JSON.parse(raw) as MultiExportPresetsFile
    if (!Array.isArray(parsed.presets)) return []
    return parsed.presets.map((preset) => ({ ...preset, isBuiltin: false }))
  } catch {
    return [...DEFAULT_MULTI_EXPORT_PRESETS_FILE.presets]
  }
}

function writeUserPresets(presets: MultiExportPreset[]): void {
  const target = storePath()
  const tmp = `${target}.tmp`
  const payload: MultiExportPresetsFile = { version: 1, presets }
  writeFileSync(tmp, JSON.stringify(payload, null, 2))
  renameSync(tmp, target)
}

function isBuiltinId(id: string): boolean {
  return BUILTIN_MULTI_EXPORT_PRESETS.some((preset) => preset.id === id)
}

export function listMultiExportPresets(): MultiExportPreset[] {
  return [...BUILTIN_MULTI_EXPORT_PRESETS, ...readUserPresets()]
}

export function createMultiExportPreset(input: { name: string; sizes: SizeRow[] }): MultiExportPreset {
  const preset: MultiExportPreset = {
    id: randomUUID(),
    name: input.name,
    sizes: input.sizes,
    isBuiltin: false
  }
  const presets = readUserPresets()
  presets.push(preset)
  writeUserPresets(presets)
  return preset
}

export function updateMultiExportPreset(
  id: string,
  patch: { name?: string; sizes?: SizeRow[] }
): MultiExportPreset {
  if (isBuiltinId(id)) throw new BuiltinPresetImmutableError(id)

  const presets = readUserPresets()
  const index = presets.findIndex((preset) => preset.id === id)
  if (index === -1) throw new PresetNotFoundError(id)

  const updated: MultiExportPreset = {
    ...presets[index],
    name: patch.name ?? presets[index].name,
    sizes: patch.sizes ?? presets[index].sizes
  }
  presets[index] = updated
  writeUserPresets(presets)
  return updated
}

export function deleteMultiExportPreset(id: string): void {
  if (isBuiltinId(id)) throw new BuiltinPresetImmutableError(id)

  const presets = readUserPresets()
  const next = presets.filter((preset) => preset.id !== id)
  if (next.length === presets.length) throw new PresetNotFoundError(id)
  writeUserPresets(next)
}

export function duplicateMultiExportPreset(id: string): MultiExportPreset {
  const source = listMultiExportPresets().find((preset) => preset.id === id)
  if (!source) throw new PresetNotFoundError(id)

  return createMultiExportPreset({
    name: `${source.name} (copia)`,
    sizes: source.sizes
  })
}
