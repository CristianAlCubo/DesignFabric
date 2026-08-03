/**
 * Store Zustand AUTOCONTENIDO del feature "Conversión de imágenes" (Utilidades).
 * Cubre dos modos independientes en un mismo tab:
 *  - `single`: convierte una imagen y la previsualiza; `POST /api/utilities/convert`
 *    devuelve `job_id`, sondeado vía `GET /api/jobs/{id}` (patrón `scale`).
 *  - `batch`: convierte N imágenes al mismo formato empaquetadas en un `.zip`;
 *    `POST /api/utilities/convert-batch` devuelve `job_id` cuyo progreso en vivo
 *    consume el componente vía `useJobProgress` (WS), finalizando con un `GET`
 *    del reporte estructurado (patrón `multi-export`).
 *
 * La exportación reutiliza los diálogos nativos ya existentes: `exportImage`
 * (imagen individual) y `downloadMultiExportZip` (guardado genérico de `.zip`).
 */
import { create } from 'zustand'

import { apiDelete, apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'

export type ConvertMode = 'single' | 'batch'
export type TargetFormat = 'JPEG' | 'JPG' | 'PNG' | 'WEBP'
export type BatchPhase = 'idle' | 'running' | 'cancelled' | 'done' | 'error'

export const TARGET_FORMATS: TargetFormat[] = ['JPEG', 'JPG', 'PNG', 'WEBP']
export const DEFAULT_QUALITY = 90

/** Extensión con la que se guarda cada formato destino (JPG/JPEG comparten `.jpg`). */
const EXTENSION_BY_FORMAT: Record<TargetFormat, string> = {
  JPEG: 'jpg',
  JPG: 'jpg',
  PNG: 'png',
  WEBP: 'webp'
}

/** El slider de calidad solo aplica a codecs con pérdida configurable. */
export function formatSupportsQuality(format: TargetFormat): boolean {
  return format !== 'PNG'
}

export function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

function stripExtension(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(0, dot) : name
}

function suggestedName(inputPath: string, format: TargetFormat): string {
  return `${stripExtension(basename(inputPath))}.${EXTENSION_BY_FORMAT[format]}`
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

interface ConvertResult {
  output_path: string
  image_url: string
}

export interface ConvertBatchItemResult {
  input: string | null
  status: 'succeeded' | 'failed'
  archive_member: string | null
  error: string | null
}

export interface ConvertBatchResult {
  zip_path: string
  zip_url: string
  expected: number
  produced: number
  items: ConvertBatchItemResult[]
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

interface ConvertState {
  mode: ConvertMode
  targetFormat: TargetFormat
  quality: number
  webpLossless: boolean

  // Modo individual
  inputPath: string | null
  inputPreview: string | null
  outputPath: string | null
  outputPreview: string | null
  isConverting: boolean
  isExporting: boolean

  // Modo lote
  images: string[]
  jobId: string | null
  batchResult: ConvertBatchResult | null
  isRunning: boolean
  phase: BatchPhase

  error: string | null

  setMode: (mode: ConvertMode) => void
  setTargetFormat: (format: TargetFormat) => void
  setQuality: (quality: number) => void
  setWebpLossless: (value: boolean) => void
  setError: (error: string | null) => void

  selectInputImage: () => Promise<void>
  runConvert: () => Promise<void>
  exportOutput: () => Promise<void>

  selectImages: () => Promise<void>
  removeImage: (path: string) => void
  clearImages: () => void
  runBatch: () => Promise<void>
  cancelBatch: () => Promise<void>
  finalizeBatch: () => Promise<void>
  downloadZip: () => Promise<void>
}

export const useImageConvertStore = create<ConvertState>((set, get) => ({
  mode: 'single',
  targetFormat: 'PNG',
  quality: DEFAULT_QUALITY,
  webpLossless: false,

  inputPath: null,
  inputPreview: null,
  outputPath: null,
  outputPreview: null,
  isConverting: false,
  isExporting: false,

  images: [],
  jobId: null,
  batchResult: null,
  isRunning: false,
  phase: 'idle',

  error: null,

  setMode: (mode) => set({ mode, error: null }),
  setTargetFormat: (targetFormat) => set({ targetFormat }),
  setQuality: (quality) => set({ quality }),
  setWebpLossless: (webpLossless) => set({ webpLossless }),
  setError: (error) => set({ error }),

  selectInputImage: async () => {
    set({ error: null })
    try {
      const path = await window.designfabric.openImageDialog()
      if (!path) return
      const preview = await window.designfabric.getImagePreview(path)
      set({ inputPath: path, inputPreview: preview, outputPath: null, outputPreview: null })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo abrir la imagen.' })
    }
  },

  runConvert: async () => {
    const state = get()
    if (!state.inputPath || state.isConverting) return

    set({ isConverting: true, error: null, outputPath: null, outputPreview: null })
    try {
      const { job_id: jobId } = await apiPost<
        { input_path: string; target_format: TargetFormat; quality: number; webp_lossless: boolean },
        { job_id: string; status: string }
      >('/api/utilities/convert', {
        input_path: state.inputPath,
        target_format: state.targetFormat,
        quality: state.quality,
        webp_lossless: state.webpLossless
      })

      const result = await waitForJob<ConvertResult>(jobId)
      const baseUrl = await getBackendBaseUrl()
      set({ outputPath: result.output_path, outputPreview: `${baseUrl}${result.image_url}` })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error al convertir la imagen.' })
    } finally {
      set({ isConverting: false })
    }
  },

  exportOutput: async () => {
    const { outputPreview, inputPath, targetFormat, isExporting } = get()
    if (!outputPreview || !inputPath || isExporting) return

    set({ isExporting: true, error: null })
    try {
      await window.designfabric.exportImage(outputPreview, suggestedName(inputPath, targetFormat))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo exportar la imagen.' })
    } finally {
      set({ isExporting: false })
    }
  },

  selectImages: async () => {
    set({ error: null })
    try {
      const paths = await window.designfabric.openImagesDialog()
      if (paths.length === 0) return
      set((state) => ({
        images: [...new Set([...state.images, ...paths])],
        batchResult: null,
        phase: 'idle'
      }))
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron seleccionar las imágenes.' })
    }
  },

  removeImage: (path) =>
    set((state) => ({ images: state.images.filter((item) => item !== path), batchResult: null })),

  clearImages: () => set({ images: [], batchResult: null }),

  runBatch: async () => {
    const state = get()
    if (state.isRunning) return
    if (state.images.length === 0) {
      set({ error: 'Selecciona al menos una imagen de entrada.' })
      return
    }

    set({ isRunning: true, phase: 'running', error: null, batchResult: null, jobId: null })
    try {
      const { job_id: jobId } = await apiPost<
        {
          image_paths: string[]
          target_format: TargetFormat
          quality: number
          webp_lossless: boolean
        },
        { job_id: string; status: string }
      >('/api/utilities/convert-batch', {
        image_paths: state.images,
        target_format: state.targetFormat,
        quality: state.quality,
        webp_lossless: state.webpLossless
      })
      set({ jobId })
      // El componente observa `jobId` con `useJobProgress` (WS) y llama a
      // `finalizeBatch()` cuando recibe el evento `completed`/`failed`.
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Error al convertir el lote.',
        phase: 'error',
        isRunning: false
      })
    }
  },

  cancelBatch: async () => {
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

  finalizeBatch: async () => {
    const { jobId } = get()
    if (!jobId) return
    try {
      const job = await apiGet<JobStatusResponse<ConvertBatchResult>>(`/api/jobs/${jobId}`)
      if (job.status === 'succeeded' && job.result) {
        // El job "succeeded" aunque algún ítem falle: la resiliencia parcial ya viene
        // reflejada en `result.produced`/`result.expected`/`result.items`.
        set({ batchResult: job.result, phase: 'done' })
      } else if (job.status === 'cancelled') {
        set({ phase: 'cancelled' })
      } else if (job.status === 'failed') {
        set({ error: job.error ?? 'Error al convertir el lote.', phase: 'error' })
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo obtener el resultado.' })
    } finally {
      set({ isRunning: false })
    }
  },

  downloadZip: async () => {
    const { batchResult, targetFormat } = get()
    if (!batchResult) return
    try {
      const baseUrl = await getBackendBaseUrl()
      await window.designfabric.downloadMultiExportZip(
        `${baseUrl}${batchResult.zip_url}`,
        `convertidas-${targetFormat.toLowerCase()}.zip`
      )
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo descargar el zip.' })
    }
  }
}))
