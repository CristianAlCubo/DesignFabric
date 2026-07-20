/** Vista batch: equivalente a `uv run designfabric --n <n>` del CLI, en la UI de escritorio. */

import { useState } from 'react'

import { ErrorBanner } from '../../core/components/ErrorBanner'
import { GenerationWorkspace } from '../../core/components/GenerationWorkspace'
import { JobProgressPanel } from '../../core/components/JobProgressPanel'
import { StickerStage } from '../../core/components/StickerStage'
import type { BatchJobResult } from '../../core/api/types'
import { useCreateBatchJob, useJob } from './api'
import { BatchForm, type BatchFormValues } from './BatchForm'
import { ResultsGallery } from './ResultsGallery'
import { useBackendBaseUrl } from './useBackendBaseUrl'

export function BatchGeneratorView() {
  const [jobId, setJobId] = useState<string | null>(null)
  const createJob = useCreateBatchJob()
  const { data: job } = useJob(jobId)
  const backendBaseUrl = useBackendBaseUrl()

  function handleSubmit(values: BatchFormValues): void {
    createJob.mutate(
      {
        num_images: values.numImages,
        ollama_model: values.ollamaModel,
        llm_provider: values.llmProvider,
        image_provider: values.imageProvider,
      },
      { onSuccess: (response) => setJobId(response.job_id) }
    )
  }

  const isSubmitting = createJob.isPending || job?.status === 'queued' || job?.status === 'running'
  const result = job?.status === 'succeeded' ? (job.result as BatchJobResult) : null

  return (
    <GenerationWorkspace
      title="Generación por lotes"
      description="Genera varios stickers en una sola pasada."
      controls={
        <div className="flex flex-col gap-4">
          <BatchForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          {createJob.isError && (
            <ErrorBanner message={createJob.error?.message ?? 'Error al encolar el job'} />
          )}
          {job?.status === 'failed' && (
            <ErrorBanner message={job.error ?? 'Error desconocido'} />
          )}
        </div>
      }
      stage={
        <div className="flex min-h-0 flex-1 flex-col">
          <StickerStage
            emptyLabel="La lámina aparecerá aquí"
            emptyHint="Elige cuántos stickers generar y pulsa Generar."
            isBusy={isSubmitting && !result}
            busyLabel="Generando lámina…"
          >
            {result && backendBaseUrl ? (
              <ResultsGallery results={result.results} backendBaseUrl={backendBaseUrl} />
            ) : undefined}
          </StickerStage>
          <JobProgressPanel jobId={jobId} />
        </div>
      }
    />
  )
}
