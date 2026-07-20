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

export type ScaleStrategyId = 'vector' | 'realesrgan'
export type SizeInputMode = 'factor' | 'manual'
export type ScaleFactor = 2 | 4
type ColorMode = 'color' | 'binary'
type TraceMode = 'spline' | 'polygon' | 'none'

export interface StrategyInfo {
  id: string
  label: string
  description?: string
}

export interface ScaleDefaults {
  dpi: number
  default_strategy?: string
  trace: {
    colormode: string
    hierarchical: string
    mode: string
    filter_speckle: number
    color_precision: number
    layer_difference: number
    corner_threshold: number
    length_threshold: number
    max_iterations: number
    splice_threshold: number
    path_precision: number
  }
  strategies?: StrategyInfo[]
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

function isScaleStrategyId(id: string): id is ScaleStrategyId {
  return id === 'vector' || id === 'realesrgan'
}

interface ScaleState {
  scaleStrategies: StrategyInfo[]
  scaleStrategiesLoaded: boolean
  selectedScaleStrategyId: ScaleStrategyId | null
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

  showAdvanced: boolean
  sizeInputMode: SizeInputMode
  scaleFactor: ScaleFactor
  width: string
  height: string
  dpi: string
  cornerThreshold: number
  colorPrecision: number
  filterSpeckle: number
  layerDifference: number
  colormode: ColorMode
  mode: TraceMode

  setSelectedScaleStrategyId: (id: ScaleStrategyId | null) => void
  setError: (error: string | null) => void
  setShowAdvanced: (value: boolean) => void
  setSizeInputMode: (value: SizeInputMode) => void
  setScaleFactor: (value: ScaleFactor) => void
  setWidth: (value: string) => void
  setHeight: (value: string) => void
  setDpi: (value: string) => void
  setCornerThreshold: (value: number) => void
  setColorPrecision: (value: number) => void
  setFilterSpeckle: (value: number) => void
  setLayerDifference: (value: number) => void
  setColormode: (value: ColorMode) => void
  setMode: (value: TraceMode) => void

  loadScaleStrategies: () => Promise<void>
  loadScaleDefaults: () => Promise<void>
  selectInputImage: () => Promise<void>
  /** Recibe un input desde otra feature (ej. "Enviar a escalado" de remove-background). */
  setInputFromExternal: (path: string, previewUrl: string) => Promise<void>
  runScale: () => Promise<void>
  exportOutput: () => Promise<void>
}

export const useScaleStore = create<ScaleState>((set, get) => ({
  scaleStrategies: [],
  scaleStrategiesLoaded: false,
  selectedScaleStrategyId: null,
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

  showAdvanced: false,
  sizeInputMode: 'factor',
  scaleFactor: 2,
  width: '',
  height: '',
  dpi: '300',
  cornerThreshold: 60,
  colorPrecision: 6,
  filterSpeckle: 4,
  layerDifference: 16,
  colormode: 'color',
  mode: 'spline',

  setSelectedScaleStrategyId: (id) => set({ selectedScaleStrategyId: id }),
  setError: (error) => set({ error }),
  setShowAdvanced: (value) => set({ showAdvanced: value }),
  setSizeInputMode: (value) => set({ sizeInputMode: value }),
  setScaleFactor: (value) => set({ scaleFactor: value }),
  setWidth: (value) => set({ width: value }),
  setHeight: (value) => set({ height: value }),
  setDpi: (value) => set({ dpi: value }),
  setCornerThreshold: (value) => set({ cornerThreshold: value }),
  setColorPrecision: (value) => set({ colorPrecision: value }),
  setFilterSpeckle: (value) => set({ filterSpeckle: value }),
  setLayerDifference: (value) => set({ layerDifference: value }),
  setColormode: (value) => set({ colormode: value }),
  setMode: (value) => set({ mode: value }),

  loadScaleStrategies: async () => {
    if (get().scaleStrategiesLoaded) return

    try {
      const defaults = await apiGet<ScaleDefaults>('/api/clearcut/scale/defaults')
      const items = defaults.strategies ?? []
      const preferred =
        items.find((item) => item.id === 'realesrgan')?.id ?? items[0]?.id ?? null
      set((state) => ({
        scaleStrategies: items,
        scaleStrategiesLoaded: true,
        selectedScaleStrategyId:
          state.selectedScaleStrategyId ??
          (preferred && isScaleStrategyId(preferred) ? preferred : 'realesrgan'),
        error: null
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron cargar las estrategias de escalado.' })
    }
  },

  loadScaleDefaults: async () => {
    if (get().scaleDefaultsLoaded) return

    try {
      const items = await apiGet<ScaleDefaults>('/api/clearcut/scale/defaults')
      // Fire-and-forget: dispara la descarga de modelos si hace falta, sin bloquear la UI.
      apiPost<Record<string, never>, unknown>('/api/clearcut/scale/ensure-models', {}).catch(
        () => undefined
      )

      const defaultStrategy =
        items.default_strategy && isScaleStrategyId(items.default_strategy)
          ? items.default_strategy
          : null
      set((state) => ({
        scaleDefaults: items,
        scaleDefaultsLoaded: true,
        dpi: String(items.dpi),
        cornerThreshold: items.trace.corner_threshold,
        colorPrecision: items.trace.color_precision,
        filterSpeckle: items.trace.filter_speckle,
        layerDifference: items.trace.layer_difference,
        colormode: items.trace.colormode === 'binary' ? 'binary' : 'color',
        mode:
          items.trace.mode === 'polygon' || items.trace.mode === 'none'
            ? items.trace.mode
            : 'spline',
        selectedScaleStrategyId: state.selectedScaleStrategyId ?? defaultStrategy ?? 'realesrgan',
        error: null
      }))
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

    const strategy = state.selectedScaleStrategyId ?? 'realesrgan'
    const dpiValue = Number(state.dpi)
    if (!Number.isFinite(dpiValue) || dpiValue <= 0) {
      set({ error: 'El DPI debe ser un número positivo.' })
      return
    }

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
          dpi?: number
          trace?: {
            corner_threshold: number
            color_precision: number
            filter_speckle: number
            layer_difference: number
            colormode: ColorMode
            mode: TraceMode
          }
        },
        { job_id: string; status: string }
      >('/api/clearcut/scale', {
        input_path: state.inputPath,
        strategy,
        width: widthPx,
        height: heightPx,
        dpi: dpiValue,
        trace:
          strategy === 'vector'
            ? {
                corner_threshold: state.cornerThreshold,
                color_precision: state.colorPrecision,
                filter_speckle: state.filterSpeckle,
                layer_difference: state.layerDifference,
                colormode: state.colormode,
                mode: state.mode
              }
            : undefined
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
