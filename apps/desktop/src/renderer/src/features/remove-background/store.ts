/**
 * Store Zustand AUTOCONTENIDO del feature "Eliminación de fondo" (ClearCut).
 * No comparte estado con `scale/store.ts` ni con `clearcut-batch/store.ts` —
 * cada feature es un módulo independiente y removible.
 *
 * La adquisición de la imagen de entrada (diálogo / portapapeles / arrastrar) y
 * la exportación del resultado viven ahora en el árbol compartido `core/imaging/`
 * (`ImageInputZone` / `ImageResultView`): el store solo guarda la entrada recibida
 * (`setInputSource`) y ejecuta el trabajo vía HTTP contra el backend único
 * (`POST /api/clearcut/remove-background` → `job_id` sondeado hasta terminar). El
 * "Enviar a escalado" se hace desde el panel con el bus de transferencia genérico.
 */
import { create } from 'zustand'

import { apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'
import { waitForJob } from '../../core/api/waitForJob'
import type { ImageSource } from '../../core/imaging/imageSource'

export interface StrategyInfo {
  id: string
  label: string
  description?: string
}

interface RemoveBackgroundResult {
  output_path: string
  image_url: string
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

  loadStrategies: () => Promise<void>
  setSelectedStrategyId: (id: string | null) => void
  setError: (error: string | null) => void
  setInputSource: (source: ImageSource) => void
  processRemoval: () => Promise<void>
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

  setInputSource: (source) => {
    set({
      inputPath: source.path,
      inputPreview: source.previewUrl,
      outputPath: null,
      outputPreview: null,
      durationSeconds: null,
      error: null
    })
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
  }
}))
