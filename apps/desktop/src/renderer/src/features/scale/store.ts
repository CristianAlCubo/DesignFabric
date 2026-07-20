/**
 * Store Zustand AUTOCONTENIDO del feature "Escalado" (ClearCut). No comparte
 * estado con `remove-background/store.ts` ni con `clearcut-batch/store.ts`.
 *
 * Reemplaza `window.clearcut.*` (IPC) por HTTP: `POST /api/clearcut/scale`
 * devuelve `job_id`, que se sondea vía `GET /api/jobs/{id}` hasta terminar.
 * La selección/exportación de imágenes usa diálogos nativos (IPC), y
 * `setInputFromExternal` es el punto de entrada que usa `remove-background`
 * para el botón "Enviar a escalado" (única acoplación intencional entre
 * ambas features, documentada en `remove-background/store.ts`).
 */
import { create } from 'zustand'

import { apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'

export type ScaleStrategyId = 'realesrgan'
export type SizeInputMode = 'factor' | 'manual'
export type ScaleFactor = 2 | 4

export interface ScaleDefaults {
  default_strategy?: string
  strategies?: { id: string; label: string; description?: string }[]
  config?: Record<string, unknown>
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

interface ScaleResult {
  output_path: string
  image_url: string
  backend: string
  device: string
  scale_factor: number
  source_size: [number, number]
  final_size: [number, number]
  inference_ms: number
  warning?: string | null
}

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

function probeImageSize(objectUrl: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      if (img.naturalWidth <= 0 || img.naturalHeight <= 0) {
        reject(new Error('No se pudo leer el tamaño de la imagen.'))
        return
      }
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
    }
    img.onerror = () => reject(new Error('No se pudo leer el tamaño de la imagen.'))
    img.src = objectUrl
  })
}

interface ScaleState {
  scaleDefaults: ScaleDefaults | null
  scaleDefaultsLoaded: boolean

  inputPath: string | null
  inputPreview: string | null
  inputWidth: number | null
  inputHeight: number | null
  outputPath: string | null
  outputPreview: string | null
  durationSeconds: number | null
  error: string | null
  warning: string | null
  isScaling: boolean
  isExporting: boolean

  sizeInputMode: SizeInputMode
  scaleFactor: ScaleFactor
  width: string
  height: string

  setError: (error: string | null) => void
  setSizeInputMode: (value: SizeInputMode) => void
  setScaleFactor: (value: ScaleFactor) => void
  setWidth: (value: string) => void
  setHeight: (value: string) => void

  loadScaleDefaults: () => Promise<void>
  selectInputImage: () => Promise<void>
  /** Recibe un input desde otra feature (ej. "Enviar a escalado" de remove-background). */
  setInputFromExternal: (path: string, previewUrl: string) => Promise<void>
  runScale: () => Promise<void>
  exportOutput: () => Promise<void>
}

export const useScaleStore = create<ScaleState>((set, get) => ({
  scaleDefaults: null,
  scaleDefaultsLoaded: false,

  inputPath: null,
  inputPreview: null,
  inputWidth: null,
  inputHeight: null,
  outputPath: null,
  outputPreview: null,
  durationSeconds: null,
  error: null,
  warning: null,
  isScaling: false,
  isExporting: false,

  sizeInputMode: 'factor',
  scaleFactor: 2,
  width: '',
  height: '',

  setError: (error) => set({ error }),
  setSizeInputMode: (value) => set({ sizeInputMode: value }),
  setScaleFactor: (value) => set({ scaleFactor: value }),
  setWidth: (value) => set({ width: value }),
  setHeight: (value) => set({ height: value }),

  loadScaleDefaults: async () => {
    if (get().scaleDefaultsLoaded) return

    try {
      const items = await apiGet<ScaleDefaults>('/api/clearcut/scale/defaults')
      apiPost<Record<string, never>, unknown>('/api/clearcut/scale/ensure-models', {}).catch(
        () => undefined
      )

      set({
        scaleDefaults: items,
        scaleDefaultsLoaded: true,
        error: null
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron cargar los defaults.' })
    }
  },

  selectInputImage: async () => {
    set({ error: null, warning: null })
    try {
      const path = await window.designfabric.openImageDialog()
      if (!path) return
      const preview = await window.designfabric.getImagePreview(path)
      const size = await probeImageSize(preview)
      set({
        inputPath: path,
        inputPreview: preview,
        inputWidth: size.width,
        inputHeight: size.height,
        outputPath: null,
        outputPreview: null,
        durationSeconds: null,
        warning: null
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo abrir el PNG.' })
    }
  },

  setInputFromExternal: async (path, previewUrl) => {
    set({ error: null, warning: null })
    try {
      const size = await probeImageSize(previewUrl)
      set({
        inputPath: path,
        inputPreview: previewUrl,
        inputWidth: size.width,
        inputHeight: size.height,
        outputPath: null,
        outputPreview: null,
        durationSeconds: null,
        warning: null
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo cargar la imagen recibida.' })
    }
  },

  runScale: async () => {
    const state = get()
    if (!state.inputPath || state.isScaling) return

    let widthPx: number | undefined
    let heightPx: number | undefined

    if (state.sizeInputMode === 'factor') {
      if (state.inputWidth === null || state.inputHeight === null) {
        set({ error: 'No se pudo determinar el tamaño de la imagen de entrada.' })
        return
      }
      widthPx = state.inputWidth * state.scaleFactor
      heightPx = state.inputHeight * state.scaleFactor
    } else {
      widthPx = state.width.trim() === '' ? undefined : Number(state.width)
      heightPx = state.height.trim() === '' ? undefined : Number(state.height)

      if (widthPx !== undefined && (!Number.isFinite(widthPx) || widthPx <= 0)) {
        set({ error: 'El ancho debe ser un número positivo.' })
        return
      }
      if (heightPx !== undefined && (!Number.isFinite(heightPx) || heightPx <= 0)) {
        set({ error: 'El alto debe ser un número positivo.' })
        return
      }
      if (widthPx === undefined && heightPx === undefined) {
        set({ error: 'Indica al menos ancho o alto en píxeles.' })
        return
      }
    }

    set({ isScaling: true, error: null, warning: null, durationSeconds: null })
    const started = performance.now()

    try {
      const { job_id: jobId } = await apiPost<
        {
          input_path: string
          strategy: ScaleStrategyId
          width?: number
          height?: number
        },
        { job_id: string; status: string }
      >('/api/clearcut/scale', {
        input_path: state.inputPath,
        strategy: 'realesrgan',
        width: widthPx,
        height: heightPx
      })

      const result = await waitForJob<ScaleResult>(jobId)
      const baseUrl = await getBackendBaseUrl()
      const durationSeconds = Math.round(((performance.now() - started) / 1000) * 100) / 100
      set({
        outputPath: result.output_path,
        outputPreview: `${baseUrl}${result.image_url}`,
        durationSeconds,
        warning: result.warning ?? null
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error al escalar la imagen.' })
    } finally {
      set({ isScaling: false })
    }
  },

  exportOutput: async () => {
    const { outputPreview, isExporting } = get()
    if (!outputPreview || isExporting) return

    set({ isExporting: true, error: null })
    try {
      await window.designfabric.exportImage(outputPreview, 'escalado.png')
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo exportar la imagen.' })
    } finally {
      set({ isExporting: false })
    }
  }
}))
