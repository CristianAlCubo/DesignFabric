/** Vista: genera una única imagen a partir de un prompt escrito por el usuario. */

import { useState } from 'react'

import { ErrorBanner } from '../../core/components/ErrorBanner'
import { JobProgressPanel } from '../../core/components/JobProgressPanel'
import type { StickerResult } from '../../core/api/types'
import { useCreateSingleImageJob, useJob } from './api'
import { SingleImageForm, type SingleImageFormValues } from './SingleImageForm'
import { SingleImageResult } from './SingleImageResult'
import { useBackendBaseUrl } from './useBackendBaseUrl'

export function SingleImageView() {
  const [jobId, setJobId] = useState<string | null>(null)
  const createJob = useCreateSingleImageJob()
  const { data: job } = useJob(jobId)
  const backendBaseUrl = useBackendBaseUrl()

  function handleSubmit(values: SingleImageFormValues): void {
    createJob.mutate(
      {
        prompt: values.prompt,
        apply_style_suffix: values.applyStyleSuffix,
        image_provider: values.imageProvider,
      },
      { onSuccess: (response) => setJobId(response.job_id) }
    )
  }

  const isSubmitting = createJob.isPending || job?.status === 'queued' || job?.status === 'running'
  const result = job?.status === 'succeeded' ? (job.result as StickerResult) : null

  return (
    <section className="view">
      <h2>Generar una imagen única</h2>
      <SingleImageForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      {createJob.isError && <ErrorBanner message={createJob.error?.message ?? 'Error al encolar el job'} />}
      {job?.status === 'failed' && <ErrorBanner message={job.error ?? 'Error desconocido'} />}
      <JobProgressPanel jobId={jobId} />
      {result && backendBaseUrl && <SingleImageResult result={result} backendBaseUrl={backendBaseUrl} />}
    </section>
  )
}
