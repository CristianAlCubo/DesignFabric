/**
 * Sondeo compartido de un job asíncrono del backend.
 *
 * Los features de imagen (remove-background, scale, halftone, image-convert)
 * encolan trabajo con `POST` que devuelve un `job_id` y luego sondean
 * `GET /api/jobs/{id}` hasta que termina. Antes cada store copiaba esta misma
 * función; ahora vive aquí una sola vez.
 */
import { apiGet } from './httpClient'

export interface JobStatusResponse<TResult> {
  id: string
  type?: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  created_at?: string
  started_at?: string | null
  finished_at?: string | null
  result: TResult | null
  error: string | null
}

/** Sondea `GET /api/jobs/{id}` cada `intervalMs` hasta que el job termine. */
export async function waitForJob<TResult>(jobId: string, intervalMs = 700): Promise<TResult> {
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
