/**
 * Presets de exportación multi-tamaño: listas con nombre de filas de tamaño (px o
 * porcentual) reutilizables entre corridas. Persistidos en `userData` (ver
 * `main/multi-export-presets.ts`); los presets de fábrica (`isBuiltin: true`) nunca se
 * escriben a disco, se mezclan en memoria al listar.
 */

export type SizeMode = 'px' | 'percent'

export interface SizeRow {
  id: string
  label: string
  mode: SizeMode
  prefix: string
  width?: number | null
  height?: number | null
  percent?: number | null
  /** Tokens soportados: {name} {width} {height} {percent} {prefix}. Default: "{prefix}{name}". */
  template?: string | null
}

export interface MultiExportPreset {
  id: string
  name: string
  sizes: SizeRow[]
  isBuiltin: boolean
}

/** Forma persistida en `multi-export-presets.json` (solo presets de usuario). */
export interface MultiExportPresetsFile {
  version: 1
  presets: MultiExportPreset[]
}

export const DEFAULT_MULTI_EXPORT_PRESETS_FILE: MultiExportPresetsFile = {
  version: 1,
  presets: []
}

/** Forma de un archivo exportado/importado por el usuario (sin `isBuiltin`). */
export interface MultiExportPresetExportFile {
  schemaVersion: 1
  presets: Array<{ name: string; sizes: SizeRow[] }>
}

/**
 * Sin presets de fábrica por defecto: la app arranca solo con los que el usuario cree.
 * Agregar uno acá alcanza para que vuelva a aparecer (protegido de edición/borrado,
 * duplicable) — ver `isBuiltinId` en `main/multi-export-presets.ts`.
 */
export const BUILTIN_MULTI_EXPORT_PRESETS: MultiExportPreset[] = []
