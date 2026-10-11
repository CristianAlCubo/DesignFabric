/**
 * Store Zustand AUTOCONTENIDO del feature "Semitonos" (Retocar).
 *
 * Dos modos:
 *  - **Rápido**: el backend elige niveles, trama y punto mínimo a partir de la imagen.
 *    El usuario solo indica la prenda (y, si quiere, el tipo de fondo).
 *  - **Avanzado**: todos los controles del Space `halftone-converter` más el punto
 *    mínimo. Al entrar se siembran con los valores que resolvió el modo rápido, y
 *    «Restablecer» vuelve a esos valores (no a los del Space).
 *
 * Dos flujos:
 *  - **Preview en vivo**: `POST /api/utilities/halftone/preview` (síncrono, baja
 *    resolución) devuelve un data URL PNG, los parámetros resueltos y los avisos de
 *    imprimibilidad; el componente lo dispara con debounce ante cada cambio.
 *  - **Guardar full-res**: al presionar «Guardar», `POST /api/utilities/halftone`
 *    devuelve `job_id`, sondeado vía `GET /api/jobs/{id}` (patrón `scale`/`convert`);
 *    el resultado es un PNG RGBA transparente @300 DPI que se ofrece de inmediato al
 *    diálogo nativo `exportImage`. En modo rápido el backend resuelve los parámetros
 *    igual que en el preview, así que el archivo coincide con lo que se veía.
 */
import { create } from 'zustand'

import { apiPost, getBackendBaseUrl } from '../../core/api/httpClient'
import { waitForJob } from '../../core/api/waitForJob'
import type { ImageSource } from '../../core/imaging/imageSource'

export type HalftoneMode = 'quick' | 'advanced'
export type Garment = 'dark' | 'light'
export type BackgroundMode = 'auto' | 'transparent' | 'black' | 'white' | 'none'
export type DetectedBackground = Exclude<BackgroundMode, 'auto'>
export type HalftoneMethod = 'halftone' | 'diffusion'
export type DotShape = 'round' | 'line'

/** Controles comunes a ambos modos. */
export interface HalftoneCommon {
  garment: Garment
  background: BackgroundMode
  backgroundThreshold: number
}

/** Controles del modo avanzado (los del Space + punto mínimo). */
export interface HalftoneAdvanced {
  blackPoint: number
  whitePoint: number
  gamma: number
  method: HalftoneMethod
  screenFrequency: number
  screenAngle: number
  dotShape: DotShape
  minDotTone: number
}

export const DEFAULT_COMMON: HalftoneCommon = {
  garment: 'dark',
  background: 'auto',
  backgroundThreshold: 25
}

/** Defaults del Space; solo se usan si aún no hay un resultado del modo rápido. */
export const DEFAULT_ADVANCED: HalftoneAdvanced = {
  blackPoint: 16,
  whitePoint: 100,
  gamma: 1.0,
  method: 'halftone',
  screenFrequency: 35,
  screenAngle: 23.5,
  dotShape: 'round',
  minDotTone: 0
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

interface ResolvedParamsPayload {
  garment: Garment
  background: DetectedBackground
  background_threshold: number
  black_point: number
  white_point: number
  gamma: number
  halftone_method: HalftoneMethod
  screen_frequency: number
  screen_angle: number
  dot_shape: DotShape
  min_dot_tone: number
}

function fromResolved(resolved: ResolvedParamsPayload): HalftoneAdvanced {
  return {
    blackPoint: resolved.black_point,
    whitePoint: resolved.white_point,
    gamma: resolved.gamma,
    method: resolved.halftone_method,
    screenFrequency: resolved.screen_frequency,
    screenAngle: resolved.screen_angle,
    dotShape: resolved.dot_shape,
    minDotTone: resolved.min_dot_tone
  }
}

/** Traduce el estado del front (camelCase) al payload del backend (snake_case). */
function toPayload(
  mode: HalftoneMode,
  common: HalftoneCommon,
  advanced: HalftoneAdvanced
): Record<string, unknown> {
  return {
    mode,
    garment: common.garment,
    background: common.background,
    background_threshold: common.backgroundThreshold,
    black_point: advanced.blackPoint,
    white_point: advanced.whitePoint,
    gamma: advanced.gamma,
    halftone_method: advanced.method,
    screen_frequency: advanced.screenFrequency,
    screen_angle: advanced.screenAngle,
    dot_shape: advanced.dotShape,
    min_dot_tone: advanced.minDotTone
  }
}

interface HalftoneResult {
  output_path: string
  image_url: string
}

interface HalftonePreviewResult {
  image_data_url: string
  width: number
  height: number
  resolved: ResolvedParamsPayload
  output_width: number
  output_height: number
  small_dot_ratio: number
  warnings: string[]
}

/** Diagnóstico del último preview. */
export interface HalftoneAnalysis {
  detectedBackground: DetectedBackground
  resolved: HalftoneAdvanced
  outputWidth: number
  outputHeight: number
  smallDotRatio: number
  warnings: string[]
}

interface HalftoneState {
  mode: HalftoneMode
  common: HalftoneCommon
  advanced: HalftoneAdvanced
  /** Valores a los que «Restablecer» devuelve en modo avanzado. */
  advancedBaseline: HalftoneAdvanced
  /** Último resultado del modo rápido (semilla del avanzado). */
  quickResolved: HalftoneAdvanced | null

  inputPath: string | null
  inputPreview: string | null

  // Preview en vivo (baja resolución).
  previewSrc: string | null
  isPreviewing: boolean
  analysis: HalftoneAnalysis | null

  // Guardado full-res (render + diálogo de guardado, en un solo paso).
  isSaving: boolean
  savedPath: string | null
  outputPath: string | null
  outputUrl: string | null

  error: string | null

  setMode: (mode: HalftoneMode) => void
  setCommon: <K extends keyof HalftoneCommon>(key: K, value: HalftoneCommon[K]) => void
  setAdvanced: <K extends keyof HalftoneAdvanced>(key: K, value: HalftoneAdvanced[K]) => void
  resetAdvanced: <K extends keyof HalftoneAdvanced>(key: K) => void
  setInputSource: (source: ImageSource) => void
  refreshPreview: () => Promise<void>
  saveFullRes: () => Promise<void>
  setError: (error: string | null) => void
}

// Descarta respuestas de preview obsoletas (llegan fuera de orden si el usuario
// mueve controles más rápido de lo que responde el backend).
let previewSeq = 0
// Resultado rápido (serializado) con el que se sembró el avanzado por última vez.
let lastSeed: string | null = null

export const useHalftoneStore = create<HalftoneState>((set, get) => ({
  mode: 'quick',
  common: { ...DEFAULT_COMMON },
  advanced: { ...DEFAULT_ADVANCED },
  advancedBaseline: { ...DEFAULT_ADVANCED },
  quickResolved: null,

  inputPath: null,
  inputPreview: null,

  previewSrc: null,
  isPreviewing: false,
  analysis: null,

  isSaving: false,
  savedPath: null,
  outputPath: null,
  outputUrl: null,

  error: null,

  setMode: (mode) => {
    const { quickResolved } = get()
    const seed = quickResolved ? JSON.stringify(quickResolved) : null
    if (mode === 'advanced' && quickResolved && seed !== lastSeed) {
      // El avanzado arranca desde lo que eligió el rápido: ajustar sobre una buena base.
      // Solo si el rápido cambió desde la última vez, para no pisar ajustes manuales
      // al ir y volver entre modos.
      lastSeed = seed
      set({
        mode,
        advanced: { ...quickResolved },
        advancedBaseline: { ...quickResolved },
        outputPath: null,
        outputUrl: null
      })
    } else {
      set({ mode, outputPath: null, outputUrl: null })
    }
  },
  setCommon: (key, value) =>
    set((state) => ({
      common: { ...state.common, [key]: value },
      outputPath: null,
      outputUrl: null
    })),
  setAdvanced: (key, value) =>
    set((state) => ({
      advanced: { ...state.advanced, [key]: value },
      outputPath: null,
      outputUrl: null
    })),
  resetAdvanced: (key) =>
    set((state) => ({
      advanced: { ...state.advanced, [key]: state.advancedBaseline[key] },
      outputPath: null,
      outputUrl: null
    })),
  setError: (error) => set({ error }),

  setInputSource: (source) => {
    set({
      inputPath: source.path,
      inputPreview: source.previewUrl,
      previewSrc: null,
      analysis: null,
      quickResolved: null,
      savedPath: null,
      outputPath: null,
      outputUrl: null,
      error: null
    })
  },

  refreshPreview: async () => {
    const { inputPath, mode, common, advanced } = get()
    if (!inputPath) return
    const seq = ++previewSeq
    set({ isPreviewing: true, error: null })
    try {
      const result = await apiPost<Record<string, unknown>, HalftonePreviewResult>(
        '/api/utilities/halftone/preview',
        {
          input_path: inputPath,
          preview_max_side: PREVIEW_MAX_SIDE,
          ...toPayload(mode, common, advanced)
        }
      )
      if (seq !== previewSeq) return
      const resolved = fromResolved(result.resolved)
      set({
        previewSrc: result.image_data_url,
        analysis: {
          detectedBackground: result.resolved.background,
          resolved,
          outputWidth: result.output_width,
          outputHeight: result.output_height,
          smallDotRatio: result.small_dot_ratio,
          warnings: result.warnings
        },
        ...(mode === 'quick' ? { quickResolved: resolved } : {})
      })
    } catch (err) {
      if (seq !== previewSeq) return
      set({ error: err instanceof Error ? err.message : 'No se pudo generar la previsualización.' })
    } finally {
      if (seq === previewSeq) set({ isPreviewing: false })
    }
  },

  saveFullRes: async () => {
    const { inputPath, mode, common, advanced, isSaving } = get()
    if (!inputPath || isSaving) return
    // El render full-res se genera on-demand al guardar y se ofrece directo al
    // diálogo nativo: el punto/tono del archivo coincide con lo que estaba en
    // pantalla al presionar (los params se capturan en el request).
    set({ isSaving: true, error: null, savedPath: null })
    try {
      const { job_id: jobId } = await apiPost<Record<string, unknown>, { job_id: string }>(
        '/api/utilities/halftone',
        { input_path: inputPath, ...toPayload(mode, common, advanced) }
      )
      const result = await waitForJob<HalftoneResult>(jobId)
      const baseUrl = await getBackendBaseUrl()
      const imageUrl = `${baseUrl}${result.image_url}`
      const saved = await window.designfabric.exportImage(
        imageUrl,
        suggestedName(inputPath)
      )
      set({
        outputPath: result.output_path,
        outputUrl: imageUrl,
        ...(saved ? { savedPath: saved } : {})
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo generar y guardar el halftone.' })
    } finally {
      set({ isSaving: false })
    }
  }
}))
