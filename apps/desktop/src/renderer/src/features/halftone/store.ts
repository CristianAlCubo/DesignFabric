/**
 * Store Zustand AUTOCONTENIDO del feature "Semitonos" (Retocar).
 *
 * Replica 1:1 las 10 opciones del Space `halftone-converter` (Gradio). Dos flujos:
 *  - **Preview en vivo**: `POST /api/utilities/halftone/preview` (síncrono, baja
 *    resolución) devuelve un data URL PNG; el componente lo dispara con debounce
 *    ante cada cambio de parámetro/imagen.
 *  - **Guardar full-res**: al presionar «Guardar», `POST /api/utilities/halftone`
 *    devuelve `job_id`, sondeado vía `GET /api/jobs/{id}` (patrón `scale`/`convert`);
 *    el resultado es un PNG RGBA transparente a 4500×5400 @300 que se ofrece de
 *    inmediato al diálogo nativo `exportImage`. El render full-res queda encapsulado
 *    en la acción de guardar: no hay un paso de «exportar» separado.
 */
import { create } from 'zustand'

import { apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'

export type HalftoneMethod = 'halftone' | 'diffusion'
export type DotShape = 'round' | 'line'

/** Los 10 controles del Gradio, con sus defaults exactos. */
export interface HalftoneParams {
  cropBlackBackground: boolean
  cropBlackThreshold: number
  blackPoint: number
  whitePoint: number
  gamma: number
  invertForDarkShirt: boolean
  method: HalftoneMethod
  screenFrequency: number
  screenAngle: number
  dotShape: DotShape
}

export const DEFAULT_PARAMS: HalftoneParams = {
  cropBlackBackground: true,
  cropBlackThreshold: 25,
  blackPoint: 16,
  whitePoint: 100,
  gamma: 1.0,
  invertForDarkShirt: false,
  method: 'halftone',
  screenFrequency: 35,
  screenAngle: 23.5,
  dotShape: 'round'
}

const PREVIEW_MAX_SIDE = 1080

export function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

function stripExtension(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(0, dot) : name
}

function suggestedName(inputPath: string): string {
  return `${stripExtension(basename(inputPath))}-halftone.png`
}

/** Traduce los params del front (camelCase) al payload del backend (snake_case). */
function toPayload(params: HalftoneParams): Record<string, unknown> {
  return {
    crop_black_background: params.cropBlackBackground,
    crop_black_threshold: params.cropBlackThreshold,
    black_point: params.blackPoint,
    white_point: params.whitePoint,
    gamma: params.gamma,
    invert_for_dark_shirt: params.invertForDarkShirt,
    halftone_method: params.method,
    screen_frequency: params.screenFrequency,
    screen_angle: params.screenAngle,
    dot_shape: params.dotShape
  }
}

interface JobStatusResponse<TResult> {
  id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  result: TResult | null
  error: string | null
}

interface HalftoneResult {
  output_path: string
  image_url: string
}

interface HalftonePreviewResult {
  image_data_url: string
  width: number
  height: number
}

async function waitForJob<TResult>(jobId: string, intervalMs = 500): Promise<TResult> {
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

interface HalftoneState {
  params: HalftoneParams

  inputPath: string | null
  inputPreview: string | null

  // Preview en vivo (baja resolución).
  previewSrc: string | null
  isPreviewing: boolean

  // Guardado full-res (render + diálogo de guardado, en un solo paso).
  isSaving: boolean
  savedPath: string | null

  error: string | null

  setParam: <K extends keyof HalftoneParams>(key: K, value: HalftoneParams[K]) => void
  resetParam: <K extends keyof HalftoneParams>(key: K) => void
  selectInputImage: () => Promise<void>
  refreshPreview: () => Promise<void>
  saveFullRes: () => Promise<void>
  setError: (error: string | null) => void
}

export const useHalftoneStore = create<HalftoneState>((set, get) => ({
  params: { ...DEFAULT_PARAMS },

  inputPath: null,
  inputPreview: null,

  previewSrc: null,
  isPreviewing: false,

  isSaving: false,
  savedPath: null,

  error: null,

  setParam: (key, value) => set((state) => ({ params: { ...state.params, [key]: value } })),
  resetParam: (key) =>
    set((state) => ({ params: { ...state.params, [key]: DEFAULT_PARAMS[key] } })),
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
        previewSrc: null,
        savedPath: null
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo abrir la imagen.' })
    }
  },

  refreshPreview: async () => {
    const { inputPath, params } = get()
    if (!inputPath) return
    set({ isPreviewing: true, error: null })
    try {
      const result = await apiPost<Record<string, unknown>, HalftonePreviewResult>(
        '/api/utilities/halftone/preview',
        { input_path: inputPath, preview_max_side: PREVIEW_MAX_SIDE, ...toPayload(params) }
      )
      set({ previewSrc: result.image_data_url })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo generar la previsualización.' })
    } finally {
      set({ isPreviewing: false })
    }
  },

  saveFullRes: async () => {
    const { inputPath, params, isSaving } = get()
    if (!inputPath || isSaving) return
    // El render full-res se genera on-demand al guardar y se ofrece directo al
    // diálogo nativo: el punto/tono del archivo coincide con lo que estaba en
    // pantalla al presionar (los params se capturan en el request).
    set({ isSaving: true, error: null, savedPath: null })
    try {
      const { job_id: jobId } = await apiPost<Record<string, unknown>, { job_id: string }>(
        '/api/utilities/halftone',
        { input_path: inputPath, ...toPayload(params) }
      )
      const result = await waitForJob<HalftoneResult>(jobId)
      const baseUrl = await getBackendBaseUrl()
      const saved = await window.designfabric.exportImage(
        `${baseUrl}${result.image_url}`,
        suggestedName(inputPath)
      )
      if (saved) set({ savedPath: saved })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo generar y guardar el halftone.' })
    } finally {
      set({ isSaving: false })
    }
  }
}))
