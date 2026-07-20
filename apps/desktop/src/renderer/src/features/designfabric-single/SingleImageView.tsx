/** Vista: genera una única imagen a partir de un prompt escrito por el usuario. */

import { ErrorBanner } from '../../core/components/ErrorBanner'
import { GenerationWorkspace } from '../../core/components/GenerationWorkspace'
import { JobProgressPanel } from '../../core/components/JobProgressPanel'
import { StickerStage } from '../../core/components/StickerStage'
import type { StickerResult } from '../../core/api/types'
import { useCreateSingleImageJob, useJob } from './api'
import { SingleImageForm } from './SingleImageForm'
import { SingleImageResult } from './SingleImageResult'
import { useGenerationSingleStore } from './store'
import { useBackendBaseUrl } from './useBackendBaseUrl'

export function SingleImageView() {
  const jobId = useGenerationSingleStore((s) => s.jobId)
  const submitError = useGenerationSingleStore((s) => s.submitError)
  const setJobId = useGenerationSingleStore((s) => s.setJobId)
  const setSubmitError = useGenerationSingleStore((s) => s.setSubmitError)
  const prompt = useGenerationSingleStore((s) => s.prompt)
  const applyStyleSuffix = useGenerationSingleStore((s) => s.applyStyleSuffix)
  const imageProvider = useGenerationSingleStore((s) => s.imageProvider)

  const createJob = useCreateSingleImageJob()
  const { data: job } = useJob(jobId)
  const backendBaseUrl = useBackendBaseUrl()

  function handleSubmit(): void {
    setSubmitError(null)
    createJob.mutate(
      {
        prompt: prompt.trim(),
        apply_style_suffix: applyStyleSuffix,
        image_provider: imageProvider
      },
      {
        onSuccess: (response) => setJobId(response.job_id),
        onError: (error) => setSubmitError(error.message || 'Error al encolar el job')
      }
    )
  }

  const isSubmitting = createJob.isPending || job?.status === 'queued' || job?.status === 'running'
  const result = job?.status === 'succeeded' ? (job.result as StickerResult) : null
  const enqueueError = submitError ?? (createJob.isError ? createJob.error?.message : null)

  return (
    <GenerationWorkspace
      title="Imagen única"
      description="Escribe un prompt y genera un sticker."
      controls={
        <div className="flex flex-col gap-4">
          <SingleImageForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          {enqueueError && <ErrorBanner message={enqueueError} />}
          {job?.status === 'failed' && (
            <ErrorBanner message={job.error ?? 'Error desconocido'} />
          )}
        </div>
      }
      stage={
        <div className="flex min-h-0 flex-1 flex-col">
          <StickerStage
            emptyLabel="Tu sticker aparecerá aquí"
            emptyHint="Escribe un prompt a la izquierda y pulsa Generar."
            isBusy={isSubmitting && !result}
            busyLabel="Generando sticker…"
          >
            {result && backendBaseUrl ? (
              <SingleImageResult result={result} backendBaseUrl={backendBaseUrl} />
            ) : undefined}
          </StickerStage>
          <JobProgressPanel jobId={jobId} />
        </div>
      }
    />
  )
}
