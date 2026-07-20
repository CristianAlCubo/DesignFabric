/** Vista nueva: genera una única imagen a partir de un prompt escrito por el usuario, sin pasar por Ollama. */

import { useState } from 'react'

import { ErrorBanner } from '../../core/components/ErrorBanner'
import { FeatureNotInstalled } from '../../core/components/FeatureNotInstalled'
import { JobProgressPanel } from '../../core/components/JobProgressPanel'
import { useLocalAiAvailability } from '../../core/hooks/useLocalAiAvailability'
import type { StickerResult } from '../../core/api/types'
import { useCreateSingleImageJob, useJob } from './api'
import { SingleImageForm } from './SingleImageForm'
import { SingleImageResult } from './SingleImageResult'
import { useBackendBaseUrl } from './useBackendBaseUrl'

export function SingleImageView() {
  const [jobId, setJobId] = useState<string | null>(null)
  const createJob = useCreateSingleImageJob()
  const { data: job } = useJob(jobId)
  const backendBaseUrl = useBackendBaseUrl()
  const localAiAvailable = useLocalAiAvailability()
  const [installedOverride, setInstalledOverride] = useState(false)

  if (localAiAvailable === false && !installedOverride) {
    return <FeatureNotInstalled onInstalled={() => setInstalledOverride(true)} />
  }

  function handleSubmit(prompt: string, applyStyleSuffix: boolean): void {
    createJob.mutate(
      { prompt, apply_style_suffix: applyStyleSuffix },
      { onSuccess: (response) => setJobId(response.job_id) }
    )
  }

  const isSubmitting = createJob.isPending || job?.status === 'queued' || job?.status === 'running'
  const result = job?.status === 'succeeded' ? (job.result as StickerResult) : null

  return (
    <section className="view">
      <h2>Generar una imagen única</h2>
      <SingleImageForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      {job?.status === 'failed' && <ErrorBanner message={job.error ?? 'Error desconocido'} />}
      <JobProgressPanel jobId={jobId} />
      {result && backendBaseUrl && <SingleImageResult result={result} backendBaseUrl={backendBaseUrl} />}
    </section>
  )
}
