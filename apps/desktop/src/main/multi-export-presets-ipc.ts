/**
 * IPC de presets de exportación multi-tamaño: CRUD sobre el store en userData +
 * import/export como archivo `.json` elegido por el usuario.
 */

import { readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import { app, dialog, ipcMain } from 'electron'

import type { MultiExportPreset, MultiExportPresetExportFile, SizeRow } from '@shared/multiExportPresets'

import { getLastImageDirectory, rememberImageDirectory } from './lastImageDirectory'
import {
  createMultiExportPreset,
  deleteMultiExportPreset,
  duplicateMultiExportPreset,
  listMultiExportPresets,
  updateMultiExportPreset
} from './multi-export-presets'

const JSON_FILTERS = [{ name: 'Presets (JSON)', extensions: ['json'] }]

function isValidSizeRow(value: unknown): value is SizeRow {
  if (typeof value !== 'object' || value === null) return false
  const row = value as Record<string, unknown>
  if (typeof row.label !== 'string' || row.label.length === 0) return false
  if (row.mode !== 'px' && row.mode !== 'percent') return false
  if (typeof row.prefix !== 'string') return false
  if (row.width !== undefined && row.width !== null && typeof row.width !== 'number') return false
  if (row.height !== undefined && row.height !== null && typeof row.height !== 'number') return false
  if (row.percent !== undefined && row.percent !== null && typeof row.percent !== 'number') return false
  if (row.template !== undefined && row.template !== null && typeof row.template !== 'string') return false
  return true
}

function parseImportFile(raw: string): Array<{ name: string; sizes: SizeRow[] }> {
  const parsed = JSON.parse(raw) as MultiExportPresetExportFile
  if (parsed.schemaVersion !== 1 || !Array.isArray(parsed.presets)) {
    throw new Error('El archivo no tiene el formato esperado de presets de exportación multi-tamaño.')
  }
  return parsed.presets.map((preset, index) => {
    if (typeof preset.name !== 'string' || preset.name.length === 0) {
      throw new Error(`El preset #${index + 1} no tiene un nombre válido.`)
    }
    if (!Array.isArray(preset.sizes) || preset.sizes.length === 0 || !preset.sizes.every(isValidSizeRow)) {
      throw new Error(`El preset "${preset.name}" tiene tamaños con formato inválido.`)
    }
    return { name: preset.name, sizes: preset.sizes }
  })
}

function uniqueName(candidate: string, existingNames: Set<string>): string {
  if (!existingNames.has(candidate)) return candidate
  let index = 2
  while (existingNames.has(`${candidate} (${index})`)) index += 1
  return `${candidate} (${index})`
}

export function registerMultiExportPresetsIpc(): void {
  ipcMain.handle('multiExport:presets:list', (): MultiExportPreset[] => listMultiExportPresets())

  ipcMain.handle(
    'multiExport:presets:create',
    (_event, input: { name: string; sizes: SizeRow[] }): MultiExportPreset =>
      createMultiExportPreset(input)
  )

  ipcMain.handle(
    'multiExport:presets:update',
    (_event, id: string, patch: { name?: string; sizes?: SizeRow[] }): MultiExportPreset =>
      updateMultiExportPreset(id, patch)
  )

  ipcMain.handle('multiExport:presets:delete', (_event, id: string): void => {
    deleteMultiExportPreset(id)
  })

  ipcMain.handle(
    'multiExport:presets:duplicate',
    (_event, id: string): MultiExportPreset => duplicateMultiExportPreset(id)
  )

  ipcMain.handle(
    'multiExport:presets:exportToFile',
    async (_event, presets: MultiExportPreset[]): Promise<string | undefined> => {
      const defaultName = presets.length === 1 ? `${presets[0].name}.json` : 'presets-exportacion.json'
      const result = await dialog.showSaveDialog({
        defaultPath: join(getLastImageDirectory() ?? app.getPath('documents'), defaultName),
        filters: JSON_FILTERS
      })
      if (result.canceled || !result.filePath) return undefined

      const payload: MultiExportPresetExportFile = {
        schemaVersion: 1,
        presets: presets.map((preset) => ({ name: preset.name, sizes: preset.sizes }))
      }
      await writeFile(result.filePath, JSON.stringify(payload, null, 2))
      rememberImageDirectory(result.filePath)
      return result.filePath
    }
  )

  ipcMain.handle('multiExport:presets:importFromFile', async (): Promise<MultiExportPreset[] | undefined> => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      defaultPath: getLastImageDirectory(),
      filters: JSON_FILTERS
    })
    if (result.canceled || result.filePaths.length === 0) return undefined

    const [filePath] = result.filePaths
    rememberImageDirectory(filePath)
    const raw = await readFile(filePath, 'utf-8')
    const incoming = parseImportFile(raw)

    const existingNames = new Set(listMultiExportPresets().map((preset) => preset.name))
    const created: MultiExportPreset[] = []
    for (const preset of incoming) {
      const name = uniqueName(preset.name, existingNames)
      existingNames.add(name)
      created.push(createMultiExportPreset({ name, sizes: preset.sizes }))
    }
    return created
  })
}
