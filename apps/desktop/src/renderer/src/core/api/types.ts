/**
 * Tipos TypeScript espejo del contrato genérico de jobs expuesto por el
 * backend único (`backend/src/designfabric/api/schemas.py`), compartido
 * por todas las features (ClearCut y DesignFabric) vía `GET/DELETE /api/jobs*`
 * y `WS /api/jobs/{id}/ws`. Mantener sincronizado a mano.
 */

export type ProgressEventType = 'started' | 'progress' | 'completed' | 'failed' | 'warning'

export interface ProgressEvent {
  job_id: string
  phase: string
  type: ProgressEventType
  current: number | null
  total: number | null
  detail: string | null
  message: string | null
  timestamp: string
}

export interface JobCreatedResponse {
  job_id: string
  status: string
}

// --- Tipos específicos de los jobs de DesignFabric (batch / single-image) ---
// Espejo de los schemas pydantic reusados por el backend único
// (`api/schemas.py`), ver detalle en `features/designfabric-batch/` y
// `features/designfabric-single/`.

export type JobType = 'batch' | 'single_image'

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export interface BatchJobRequest {
  num_images: number
  ollama_model?: string
}

export interface SingleImageJobRequest {
  prompt: string
  apply_style_suffix?: boolean
}

export interface StickerResult {
  prompt: string
  filename: string | null
  image_url: string | null
  success: boolean
  error: string | null
}

export interface BatchJobResult {
  prompts: string[]
  results: StickerResult[]
  failure_count: number
}

export interface JobStatusResponse {
  id: string
  type: JobType
  status: JobStatus
  created_at: string
  started_at: string | null
  finished_at: string | null
  result: BatchJobResult | StickerResult | null
  error: string | null
}
