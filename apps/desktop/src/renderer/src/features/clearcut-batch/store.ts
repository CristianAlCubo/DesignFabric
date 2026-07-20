/**
 * Store Zustand AUTOCONTENIDO del feature "Lote" (ClearCut batch). No
 * comparte estado con `remove-background/store.ts` ni con `scale/store.ts`.
 *
 * Reemplaza `window.clearcut.*` (IPC de procesamiento) por HTTP:
 * `POST /api/clearcut/batch` devuelve `job_id`. El progreso en vivo (archivo
 * actual, avance) se obtiene en el componente vía `useJobProgress`
 * (WebSocket, ver `core/hooks`); este store solo guarda el `job_id` activo y,
 * al terminar, hace un `GET /api/jobs/{id}` final para obtener el reporte
 * estructurado completo. La selección de carpeta/archivos de entrada y de
 * salida SÍ usa IPC (diálogos nativos), igual que en el ClearCut original.
 */
import { create } from 'zustand'

import { apiDelete, apiGet, apiPost } from '../../core/api/httpClient'

export type BatchInputMode = 'folder' | 'files'
export type ScaleFactor = 2 | 4
export type BatchItemStatus = 'succeeded' | 'failed' | 'skipped'
export type BatchJobPhase = 'idle' | 'running' | 'cancelled' | 'done' | 'error'

export interface StrategyInfo {
  id: string
  label: string
  description?: string
}

export interface BatchItemResult {
  input: string
  output: string | null
  status: BatchItemStatus
  error: string | null
  warning: string | null
}

export interface BatchReport {
  total: number
  succeeded: number
  failed: number
  skipped: number
  cancelled?: boolean
  items: BatchItemResult[]
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

interface BatchState {
  strategies: StrategyInfo[]
  strategiesLoaded: boolean

  batchInputMode: BatchInputMode
  batchInputDir: string | null
  batchInputFiles: string[]
  /** Conteo de imágenes de entrada (carpeta escaneada o archivos seleccionados). */
  batchInputCount: number | null
  batchOutputDir: string
  batchRemovalStrategyId: string | null
  batchFactor: ScaleFactor

  jobId: string | null
  batchReport: BatchReport | null
  batchError: string | null
  isBatchRunning: boolean
  batchPhase: BatchJobPhase

  loadStrategies: () => Promise<void>
  setBatchInputMode: (mode: BatchInputMode) => void
  selectBatchFolder: () => Promise<void>
  selectBatchFiles: () => Promise<void>
  selectBatchOutputDir: () => Promise<void>
  setBatchRemovalStrategyId: (id: string | null) => void
  setBatchFactor: (factor: ScaleFactor) => void
  setBatchError: (error: string | null) => void
  runBatch: () => Promise<void>
  cancelBatch: () => Promise<void>
  openBatchOutputDir: () => Promise<void>
  /** Llamado por el componente al recibir (vía WS) que el job terminó. */
  finalizeJob: () => Promise<void>
}

export const useBatchStore = create<BatchState>((set, get) => ({
  strategies: [],
  strategiesLoaded: false,

  batchInputMode: 'folder',
  batchInputDir: null,
  batchInputFiles: [],
  batchInputCount: null,
  batchOutputDir: '',
  batchRemovalStrategyId: null,
  batchFactor: 2,

  jobId: null,
  batchReport: null,
  batchError: null,
  isBatchRunning: false,
  batchPhase: 'idle',

  loadStrategies: async () => {
    if (get().strategiesLoaded) return
    try {
      const items = await apiGet<StrategyInfo[]>('/api/clearcut/strategies')
      const preferred = items.find((item) => item.id === 'white_background')?.id ?? items[0]?.id ?? null
      set((state) => ({
        strategies: items,
        strategiesLoaded: true,
        batchRemovalStrategyId: state.batchRemovalStrategyId ?? preferred
      }))
    } catch (err) {
      set({ batchError: err instanceof Error ? err.message : 'No se pudieron cargar las estrategias.' })
    }
  },

  setBatchInputMode: (mode) =>
    set((state) => ({
      batchInputMode: mode,
      batchInputDir: mode === 'folder' ? state.batchInputDir : null,
      batchInputFiles: mode === 'files' ? state.batchInputFiles : [],
      batchInputCount:
        mode === 'folder'
          ? state.batchInputDir
            ? state.batchInputCount
            : null
          : state.batchInputFiles.length > 0
            ? state.batchInputFiles.length
            : null,
      batchReport: null,
      batchError: null
    })),

  selectBatchFolder: async () => {
    set({ batchError: null })
    try {
      const directory = await window.designfabric.openDirectoryDialog()
      if (!directory) return
      const count = await window.designfabric.countImagesInDirectory(directory)
      set({
        batchInputMode: 'folder',
        batchInputDir: directory,
        batchInputFiles: [],
        batchInputCount: count,
        batchReport: null
      })
    } catch (err) {
      set({ batchError: err instanceof Error ? err.message : 'No se pudo seleccionar la carpeta.' })
    }
  },

  selectBatchFiles: async () => {
    set({ batchError: null })
    try {
      const paths = await window.designfabric.openImagesDialog()
      if (paths.length === 0) return
      set({
        batchInputMode: 'files',
        batchInputFiles: paths,
        batchInputDir: null,
        batchInputCount: paths.length,
        batchReport: null
      })
    } catch (err) {
      set({ batchError: err instanceof Error ? err.message : 'No se pudieron seleccionar las imágenes.' })
    }
  },

  selectBatchOutputDir: async () => {
    set({ batchError: null })
    try {
      const directory = await window.designfabric.openDirectoryDialog()
      if (!directory) return
      set({ batchOutputDir: directory, batchReport: null })
    } catch (err) {
      set({ batchError: err instanceof Error ? err.message : 'No se pudo seleccionar la carpeta de salida.' })
    }
  },

  setBatchRemovalStrategyId: (id) => set({ batchRemovalStrategyId: id }),
  setBatchFactor: (factor) => set({ batchFactor: factor }),
  setBatchError: (error) => set({ batchError: error }),

  runBatch: async () => {
    const state = get()
    if (state.isBatchRunning) return

    const removalStrategy = state.batchRemovalStrategyId ?? 'white_background'

    const hasInput =
      state.batchInputMode === 'folder' ? Boolean(state.batchInputDir) : state.batchInputFiles.length > 0
    const outputDir = state.batchOutputDir.trim()

    if (!hasInput || !outputDir) {
      set({
        batchError: 'Selecciona una entrada y escribe una carpeta de salida antes de procesar.',
        batchPhase: 'error'
      })
      return
    }

    if (state.batchInputCount === 0) {
      set({
        batchError: 'La entrada no contiene imágenes compatibles (png, jpg, jpeg, webp).',
        batchPhase: 'error'
      })
      return
    }

    set({
      isBatchRunning: true,
      batchPhase: 'running',
      batchError: null,
      batchReport: null,
      jobId: null
    })

    try {
      apiPost<Record<string, never>, unknown>('/api/clearcut/scale/ensure-models', {}).catch(
        () => undefined
      )

      const { job_id: jobId } = await apiPost<
        {
          input:
            | { kind: 'folder'; directory: string }
            | { kind: 'files'; paths: string[] }
          output_dir: string
          removal_strategy: string
          scale_strategy: 'realesrgan'
          factor: ScaleFactor
        },
        { job_id: string; status: string }
      >('/api/clearcut/batch', {
        input:
          state.batchInputMode === 'folder'
            ? { kind: 'folder', directory: state.batchInputDir as string }
            : { kind: 'files', paths: state.batchInputFiles },
        output_dir: outputDir,
        removal_strategy: removalStrategy,
        scale_strategy: 'realesrgan',
        factor: state.batchFactor
      })

      set({ jobId })
      // El componente observa este `jobId` con `useJobProgress` (WS) y llama
      // a `finalizeJob()` cuando recibe el evento `completed`/`failed`.
    } catch (err) {
      set({
        batchError: err instanceof Error ? err.message : 'Error al procesar el lote.',
        batchPhase: 'error',
        isBatchRunning: false
      })
    }
  },

  cancelBatch: async () => {
    const { jobId, isBatchRunning } = get()
    if (!jobId || !isBatchRunning) return
    try {
      await apiDelete(`/api/jobs/${jobId}`)
      set({ batchPhase: 'cancelled', isBatchRunning: false })
    } catch (err) {
      set({
        batchError:
          err instanceof Error
            ? err.message
            : 'No se pudo cancelar el lote (probablemente ya está en curso).'
      })
    }
  },

  finalizeJob: async () => {
    const { jobId } = get()
    if (!jobId) return
    try {
      const job = await apiGet<JobStatusResponse<BatchReport>>(`/api/jobs/${jobId}`)
      if (job.status === 'succeeded' && job.result) {
        set({ batchReport: job.result, batchPhase: job.result.cancelled ? 'cancelled' : 'done' })
      } else if (job.status === 'cancelled') {
        set({ batchPhase: 'cancelled' })
      } else if (job.status === 'failed') {
        set({ batchError: job.error ?? 'Error al procesar el lote.', batchPhase: 'error' })
      }
    } catch (err) {
      set({ batchError: err instanceof Error ? err.message : 'No se pudo obtener el resultado del lote.' })
    } finally {
      set({ isBatchRunning: false })
    }
  },

  openBatchOutputDir: async () => {
    const { batchOutputDir } = get()
    if (!batchOutputDir) return
    try {
      const error = await window.designfabric.openPath(batchOutputDir)
      if (error) set({ batchError: error })
    } catch (err) {
      set({ batchError: err instanceof Error ? err.message : 'No se pudo abrir la carpeta de salida.' })
    }
  }
}))
