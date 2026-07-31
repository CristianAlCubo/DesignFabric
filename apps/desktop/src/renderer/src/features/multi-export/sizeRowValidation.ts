/**
 * Reglas de validación de una fila de tamaño y de un preset completo, compartidas por el
 * store (guard de `runExport`), `SizeRowEditor` (estilo de error inline) y
 * `PresetManagerDialog` (habilitar "Guardar"/"Crear preset").
 */
import type { SizeRow } from '@shared/multiExportPresets'

export function isSizeRowValid(row: SizeRow): boolean {
  if (row.label.trim().length === 0) return false
  if (row.mode === 'percent') {
    return typeof row.percent === 'number' && Number.isFinite(row.percent) && row.percent > 0
  }
  const width = row.width
  const height = row.height
  const widthOk = typeof width === 'number' && Number.isFinite(width) && width > 0
  const heightOk = typeof height === 'number' && Number.isFinite(height) && height > 0
  if (width != null && !widthOk) return false
  if (height != null && !heightOk) return false
  return widthOk || heightOk
}

export function isPresetDraftValid(name: string, sizes: SizeRow[]): boolean {
  return name.trim().length > 0 && sizes.length > 0 && sizes.every(isSizeRowValid)
}
