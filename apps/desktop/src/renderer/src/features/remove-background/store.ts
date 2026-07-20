/**
 * Store Zustand AUTOCONTENIDO del feature "Eliminación de fondo" (ClearCut).
 * No comparte estado con `scale/store.ts` ni con `clearcut-batch/store.ts` —
 * cada feature es un módulo independiente y removible. La única excepción
 * deliberada es `sendToScale()`, que importa el store de `scale` directamente
 * porque es, por diseño, una acción cruzada entre exactamente estas dos
 * features (igual que en el ClearCut original).
 *
 * Reemplaza el antiguo `window.clearcut.*` (IPC síncrono) por HTTP contra el
 * backend único: `POST /api/clearcut/remove-background` devuelve un `job_id`
 * que se sondea (`polling`) vía `GET /api/jobs/{id}` hasta que termina. La
 * selección de archivos y la exportación del resultado sí usan IPC (diálogos
 * nativos), porque son inherentemente de Electron.
 */
import { create } from 'zustand'

import { apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'
import { useNavigationStore } from '../../core/state/navigationStore'
import { useScaleStore } from '../scale/store'

export interface StrategyInfo {
  id: string
  label: string
  description?: string
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

interface RemoveBackgroundResult {
  output_path: string
  image_url: string
}

/** Sondea `GET /api/jobs/{id}` cada `intervalMs` hasta que el job termine. */
async function waitForJob<TResult>(jobId: string, intervalMs = 700): Promise<TResult> {
  for (;;) {
    const job = await apiGet<JobStatusResponse<TResult>>(`/api/jobs/${jobId}`)
    if (job.status === 'succeeded') {
      if (!job.result) throw new Error('El job terminó sin resultado.')
      return job.result
    }
    if (job.status === 'failed') throw new Error(job.error ?? 'El job falló.')
    if (job.status === 'cancelled') throw new Error('El job fue cancelado.')
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
}

interface RemoveBackgroundState {
  strategies: StrategyInfo[]
  strategiesLoaded: boolean
  selectedStrategyId: string | null

  inputPath: string | null
  inputPreview: string | null
  outputPath: string | null
  outputPreview: string | null
  durationSeconds: number | null
  error: string | null
  isProcessing: boolean
  isExporting: boolean

  loadStrategies: () => Promise<void>
  setSelectedStrategyId: (id: string | null) => void
  setError: (error: string | null) => void
  selectInputImage: () => Promise<void>
  processRemoval: () => Promise<void>
  exportOutput: () => Promise<void>
  sendToScale: () => void
}

export const useRemoveBackgroundStore = create<RemoveBackgroundState>((set, get) => ({
  strategies: [],
  strategiesLoaded: false,
  selectedStrategyId: null,

  inputPath: null,
  inputPreview: null,
  outputPath: null,
  outputPreview: null,
  durationSeconds: null,
  error: null,
  isProcessing: false,
  isExporting: false,

  loadStrategies: async () => {
    if (get().strategiesLoaded) return

    try {
      const items = await apiGet<StrategyInfo[]>('/api/clearcut/strategies')
      const preferred = items.find((item) => item.id === 'white_background')?.id ?? items[0]?.id ?? null
      set((state) => ({
        strategies: items,
        strategiesLoaded: true,
        selectedStrategyId: state.selectedStrategyId ?? preferred,
        error: null
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron cargar las estrategias.' })
    }
  },

  setSelectedStrategyId: (id) => set({ selectedStrategyId: id }),
  setError: (error) => set({ error }),

  selectInputImage: async () => {
    set({ error: null })
    try {
      const path = await window.designfabric.openImageDialog()
      if (!path) return
      const preview = await window.designfabric.getImagePreview(path)
      set({
        inputPath: path,
        inputPreview: preview,
        outputPath: null,
        outputPreview: null,
        durationSeconds: null
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo abrir la imagen.' })
    }
  },

  processRemoval: async () => {
    const { inputPath, selectedStrategyId, isProcessing } = get()
    if (!inputPath || !selectedStrategyId || isProcessing) return

    set({ isProcessing: true, error: null, durationSeconds: null })
    const started = performance.now()

    try {
      const { job_id: jobId } = await apiPost<
        { input_path: string; strategy: string },
        { job_id: string; status: string }
      >('/api/clearcut/remove-background', { input_path: inputPath, strategy: selectedStrategyId })

      const result = await waitForJob<RemoveBackgroundResult>(jobId)
      const baseUrl = await getBackendBaseUrl()
      const durationSeconds = Math.round(((performance.now() - started) / 1000) * 100) / 100
      set({
        outputPath: result.output_path,
        outputPreview: `${baseUrl}${result.image_url}`,
        durationSeconds
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error al procesar la imagen.' })
    } finally {
      set({ isProcessing: false })
    }
  },

  exportOutput: async () => {
    const { outputPreview, isExporting } = get()
    if (!outputPreview || isExporting) return

    set({ isExporting: true, error: null })
    try {
      await window.designfabric.exportImage(outputPreview, 'sin-fondo.png')
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo exportar la imagen.' })
    } finally {
      set({ isExporting: false })
    }
  },

  sendToScale: () => {
    const { outputPath, outputPreview } = get()
    if (!outputPath || !outputPreview) return
    useScaleStore.getState().setInputFromExternal(outputPath, outputPreview)
    useNavigationStore.getState().setActiveTab('scale')
  }
}))
