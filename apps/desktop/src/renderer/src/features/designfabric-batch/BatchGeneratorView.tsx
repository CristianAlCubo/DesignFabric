/** Vista batch: equivalente a `uv run designfabric --n <n>` del CLI, en la UI de escritorio. */

import { ErrorBanner } from '../../core/components/ErrorBanner'
import { GenerationWorkspace } from '../../core/components/GenerationWorkspace'
import { JobProgressPanel } from '../../core/components/JobProgressPanel'
import { StickerStage } from '../../core/components/StickerStage'
import type { BatchJobResult } from '../../core/api/types'
import { useCancelJob, useCreateBatchJob, useJob } from './api'
import { BatchForm } from './BatchForm'
import { ResultsGallery } from './ResultsGallery'
import { useGenerationBatchStore } from './store'
import { useBackendBaseUrl } from './useBackendBaseUrl'

export function BatchGeneratorView() {
  const jobId = useGenerationBatchStore((s) => s.jobId)
  const submitError = useGenerationBatchStore((s) => s.submitError)
  const setJobId = useGenerationBatchStore((s) => s.setJobId)
  const setSubmitError = useGenerationBatchStore((s) => s.setSubmitError)
  const numImages = useGenerationBatchStore((s) => s.numImages)
  const ollamaModel = useGenerationBatchStore((s) => s.ollamaModel)
  const llmProvider = useGenerationBatchStore((s) => s.llmProvider)
  const imageProvider = useGenerationBatchStore((s) => s.imageProvider)
  const transparentBackground = useGenerationBatchStore((s) => s.transparentBackground)

  const createJob = useCreateBatchJob()
  const cancelJob = useCancelJob()
  const { data: job } = useJob(jobId)
  const backendBaseUrl = useBackendBaseUrl()

  function handleSubmit(): void {
    setSubmitError(null)
    createJob.mutate(
      {
        num_images: numImages,
        ollama_model: ollamaModel,
        llm_provider: llmProvider,
        image_provider: imageProvider,
        transparent_background: transparentBackground
      },
      {
        onSuccess: (response) => setJobId(response.job_id),
        onError: (error) => setSubmitError(error.message || 'Error al encolar el job')
      }
    )
  }

  function handleCancel(): void {
    if (!jobId) return
    cancelJob.mutate(jobId, {
      onError: (error) => setSubmitError(error.message || 'No se pudo cancelar el job')
    })
  }

  const isSubmitting = createJob.isPending || job?.status === 'queued' || job?.status === 'running'
  const result =
    job?.status === 'succeeded' || job?.status === 'cancelled'
      ? (job.result as BatchJobResult | null)
      : null
  const enqueueError = submitError ?? (createJob.isError ? createJob.error?.message : null)

  return (
    <GenerationWorkspace
      title="Generación por lotes"
      description="Genera varios stickers en una sola pasada."
      controls={
        <div className="flex flex-col gap-4">
          <BatchForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          {enqueueError && <ErrorBanner message={enqueueError} />}
          {job?.status === 'failed' && (
            <ErrorBanner message={job.error ?? 'Error desconocido'} />
          )}
          {job?.status === 'cancelled' && (
            <p className="text-sm text-muted-foreground">Generación cancelada.</p>
          )}
        </div>
      }
      stage={
        <div className="flex min-h-0 flex-1 flex-col">
          <StickerStage
            emptyLabel="La lámina aparecerá aquí"
            emptyHint="Elige cuántos stickers generar y pulsa Generar."
            isBusy={isSubmitting && !result?.results?.length}
            busyLabel="Generando lámina…"
          >
            {result?.results?.length && backendBaseUrl ? (
              <ResultsGallery results={result.results} backendBaseUrl={backendBaseUrl} />
            ) : undefined}
          </StickerStage>
          <JobProgressPanel
            jobId={jobId}
            cancellable={isSubmitting}
            cancelling={cancelJob.isPending}
            onCancel={handleCancel}
          />
        </div>
      }
    />
  )
}
