/**
 * Store Zustand AUTOCONTENIDO del feature "Multi-tamaño": exporta N imágenes contra
 * una lista de tamaños (preset o ad-hoc) empaquetadas en un `.zip`. No comparte estado
 * con `scale/store.ts` ni `clearcut-batch/store.ts`.
 *
 * `POST /api/clearcut/multi-export` devuelve `job_id`; el progreso en vivo lo consume el
 * componente vía `useJobProgress` (WS) — este store solo guarda el `job_id` activo y, al
 * terminar, hace un `GET /api/jobs/{id}` final para obtener el reporte estructurado. Los
 * presets viven en `userData` (proceso main) y se manipulan vía IPC (`window.designfabric`).
 */
import { create } from 'zustand'

import type { MultiExportPreset, SizeMode, SizeRow } from '@shared/multiExportPresets'

import { apiDelete, apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'
import { isSizeRowValid } from './sizeRowValidation'

export type MultiExportPhase = 'idle' | 'running' | 'cancelled' | 'done' | 'error'

export interface MultiExportItemResult {
  input: string | null
  size_label: string
  status: 'succeeded' | 'failed'
  archive_member: string | null
  error: string | null
}

export interface MultiExportResult {
  zip_path: string
  zip_url: string
  expected: number
  produced: number
  items: MultiExportItemResult[]
}

interface JobStatusResponse<TResult> {
  id: string
  type: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  created_at: string
  started_at: string | null
  finished_at: string | null
  result: TResult | null
  error: string | null
}

export function createDefaultSizeRow(): SizeRow {
  return {
    id: crypto.randomUUID(),
    label: 'Nuevo tamaño',
    mode: 'px',
    prefix: '',
    width: 512,
    height: null,
    percent: null,
    template: null
  }
}

interface MultiExportState {
  images: string[]

  presets: MultiExportPreset[]
  presetsLoaded: boolean
  selectedPresetId: string | null
  /** Copia editable de las filas de tamaño de la corrida actual (independiente del preset guardado). */
  activeSizes: SizeRow[]

  jobId: string | null
  result: MultiExportResult | null
  error: string | null
  isRunning: boolean
  phase: MultiExportPhase

  loadPresets: () => Promise<void>
  selectImages: () => Promise<void>
  removeImage: (path: string) => void
  clearImages: () => void

  selectPreset: (id: string | null) => void
  addSizeRow: () => void
  updateSizeRow: (id: string, patch: Partial<SizeRow>) => void
  removeSizeRow: (id: string) => void

  createPreset: (input: { name: string; sizes: SizeRow[] }) => Promise<MultiExportPreset | undefined>
  updatePreset: (id: string, patch: { name?: string; sizes?: SizeRow[] }) => Promise<MultiExportPreset | undefined>
  deletePreset: (id: string) => Promise<void>
  duplicatePreset: (id: string) => Promise<MultiExportPreset | undefined>
  exportPreset: (id: string) => Promise<void>
  importPresets: () => Promise<MultiExportPreset[] | undefined>

  setError: (error: string | null) => void
  runExport: () => Promise<void>
  cancelExport: () => Promise<void>
  finalizeJob: () => Promise<void>
  downloadZip: () => Promise<void>
}

export const useMultiExportStore = create<MultiExportState>((set, get) => ({
  images: [],

  presets: [],
  presetsLoaded: false,
  selectedPresetId: null,
  activeSizes: [createDefaultSizeRow()],

  jobId: null,
  result: null,
  error: null,
  isRunning: false,
  phase: 'idle',

  loadPresets: async () => {
    if (get().presetsLoaded) return
    try {
      const presets = await window.designfabric.listMultiExportPresets()
      set({ presets, presetsLoaded: true })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron cargar los presets.' })
    }
  },

  selectImages: async () => {
    set({ error: null })
    try {
      const paths = await window.designfabric.openImagesDialog()
      if (paths.length === 0) return
      set((state) => ({
        images: [...new Set([...state.images, ...paths])],
        result: null,
        phase: 'idle'
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron seleccionar las imágenes.' })
    }
  },

  removeImage: (path) =>
    set((state) => ({ images: state.images.filter((item) => item !== path), result: null })),

  clearImages: () => set({ images: [], result: null }),

  selectPreset: (id) => {
    if (id === null) {
      set({ selectedPresetId: null })
      return
    }
    const preset = get().presets.find((item) => item.id === id)
    if (!preset) return
    set({
      selectedPresetId: id,
      activeSizes: preset.sizes.map((row) => ({ ...row }))
    })
  },

  addSizeRow: () => set((state) => ({ activeSizes: [...state.activeSizes, createDefaultSizeRow()] })),

  updateSizeRow: (id, patch) =>
    set((state) => ({
      activeSizes: state.activeSizes.map((row) => (row.id === id ? { ...row, ...patch } : row))
    })),

  removeSizeRow: (id) =>
    set((state) => ({ activeSizes: state.activeSizes.filter((row) => row.id !== id) })),

  createPreset: async (input) => {
    try {
      const preset = await window.designfabric.createMultiExportPreset(input)
      set((state) => ({ presets: [...state.presets, preset] }))
      return preset
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo crear el preset.' })
      return undefined
    }
  },

  updatePreset: async (id, patch) => {
    try {
      const updated = await window.designfabric.updateMultiExportPreset(id, patch)
      set((state) => ({
        presets: state.presets.map((preset) => (preset.id === updated.id ? updated : preset))
      }))
      return updated
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo actualizar el preset.' })
      return undefined
    }
  },

  deletePreset: async (id) => {
    try {
      await window.designfabric.deleteMultiExportPreset(id)
      set((state) => ({
        presets: state.presets.filter((preset) => preset.id !== id),
        selectedPresetId: state.selectedPresetId === id ? null : state.selectedPresetId
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo eliminar el preset.' })
    }
  },

  duplicatePreset: async (id) => {
    try {
      const copy = await window.designfabric.duplicateMultiExportPreset(id)
      set((state) => ({ presets: [...state.presets, copy] }))
      return copy
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo duplicar el preset.' })
      return undefined
    }
  },

  exportPreset: async (id) => {
    const preset = get().presets.find((item) => item.id === id)
    if (!preset) return
    try {
      await window.designfabric.exportMultiExportPresetsToFile([preset])
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo exportar el preset.' })
    }
  },

  importPresets: async () => {
    try {
      const imported = await window.designfabric.importMultiExportPresetsFromFile()
      if (!imported || imported.length === 0) return undefined
      set((state) => ({ presets: [...state.presets, ...imported] }))
      return imported
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo importar el archivo de presets.' })
      return undefined
    }
  },

  setError: (error) => set({ error }),

  runExport: async () => {
    const state = get()
    if (state.isRunning) return
    if (state.images.length === 0) {
      set({ error: 'Selecciona al menos una imagen de entrada.' })
      return
    }
    if (state.activeSizes.length === 0) {
      set({ error: 'Agrega al menos un tamaño a exportar.' })
      return
    }
    if (!state.activeSizes.every(isSizeRowValid)) {
      set({ error: 'Revisa los tamaños: hay filas incompletas.' })
      return
    }

    set({ isRunning: true, phase: 'running', error: null, result: null, jobId: null })

    try {
      const { job_id: jobId } = await apiPost<
        {
          image_paths: string[]
          sizes: Array<{
            label: string
            mode: SizeMode
            prefix: string
            width?: number | null
            height?: number | null
            percent?: number | null
            template?: string | null
          }>
        },
        { job_id: string; status: string }
      >('/api/clearcut/multi-export', {
        image_paths: state.images,
        sizes: state.activeSizes.map((row) => ({
          label: row.label,
          mode: row.mode,
          prefix: row.prefix,
          width: row.width ?? undefined,
          height: row.height ?? undefined,
          percent: row.percent ?? undefined,
          template: row.template ?? undefined
        }))
      })
      set({ jobId })
      // El componente observa `jobId` con `useJobProgress` (WS) y llama a
      // `finalizeJob()` cuando recibe el evento `completed`/`failed`.
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Error al exportar.',
        phase: 'error',
        isRunning: false
      })
    }
  },

  cancelExport: async () => {
    const { jobId, isRunning } = get()
    if (!jobId || !isRunning) return
    try {
      await apiDelete(`/api/jobs/${jobId}`)
      set({ phase: 'cancelled', isRunning: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'No se pudo cancelar (probablemente ya está en curso).'
      })
    }
  },

  finalizeJob: async () => {
    const { jobId } = get()
    if (!jobId) return
    try {
      const job = await apiGet<JobStatusResponse<MultiExportResult>>(`/api/jobs/${jobId}`)
      if (job.status === 'succeeded' && job.result) {
        // El job siempre "succeeded" aunque algunas combinaciones fallen — la resiliencia
        // parcial ya viene reflejada en `result.produced`/`result.expected`/`result.items`.
        set({ result: job.result, phase: 'done' })
      } else if (job.status === 'cancelled') {
        set({ phase: 'cancelled' })
      } else if (job.status === 'failed') {
        set({ error: job.error ?? 'Error al exportar.', phase: 'error' })
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo obtener el resultado.' })
    } finally {
      set({ isRunning: false })
    }
  },

  downloadZip: async () => {
    const { result } = get()
    if (!result) return
    try {
      const baseUrl = await getBackendBaseUrl()
      await window.designfabric.downloadMultiExportZip(`${baseUrl}${result.zip_url}`, 'export.zip')
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo descargar el zip.' })
    }
  }
}))
