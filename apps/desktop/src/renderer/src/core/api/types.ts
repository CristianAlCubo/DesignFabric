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

export type LlmProviderId = 'ollama' | 'openrouter' | 'test'
export type ImageProviderId = 'flux' | 'openrouter' | 'test'

export interface ProviderInfo {
  id: string
  label: string
  available: boolean
  requires_local_ai: boolean
}

export interface GenerationProvidersResponse {
  llm: ProviderInfo[]
  image: ProviderInfo[]
}

export interface GenerationReadiness {
  local_ai: {
    available: boolean
    missing: string[]
  }
  ollama: {
    host: string
    reachable: boolean
    models: string[]
    error: string | null
  }
  flux: {
    model_id: string
    weights_present: boolean
    cache_hint: string | null
  }
  cuda: {
    available: boolean
    device_name: string | null
  }
  providers: {
    ollama: boolean
    flux: boolean
    test_llm: boolean
    test_image: boolean
    openrouter_llm?: boolean
    openrouter_image?: boolean
  }
  openrouter?: {
    configured: boolean
    text_model_id: string | null
    image_model_id: string | null
  }
}

export interface BatchJobRequest {
  num_images: number
  ollama_model?: string
  llm_provider?: LlmProviderId
  image_provider?: ImageProviderId
  transparent_background?: boolean
}

export interface SingleImageJobRequest {
  prompt: string
  apply_style_suffix?: boolean
  image_provider?: ImageProviderId
  transparent_background?: boolean
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
  cancelled?: boolean
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
