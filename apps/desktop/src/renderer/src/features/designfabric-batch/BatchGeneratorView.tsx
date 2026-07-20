/** Vista batch: equivalente a `uv run designfabric --n <n>` del CLI, en la UI de escritorio. */

import { useState } from 'react'

import { ErrorBanner } from '../../core/components/ErrorBanner'
import { FeatureNotInstalled } from '../../core/components/FeatureNotInstalled'
import { JobProgressPanel } from '../../core/components/JobProgressPanel'
import { useLocalAiAvailability } from '../../core/hooks/useLocalAiAvailability'
import type { BatchJobResult } from '../../core/api/types'
import { useCreateBatchJob, useJob } from './api'
import { BatchForm } from './BatchForm'
import { ResultsGallery } from './ResultsGallery'
import { useBackendBaseUrl } from './useBackendBaseUrl'

export function BatchGeneratorView() {
  const [jobId, setJobId] = useState<string | null>(null)
  const createJob = useCreateBatchJob()
  const { data: job } = useJob(jobId)
  const backendBaseUrl = useBackendBaseUrl()
  const localAiAvailable = useLocalAiAvailability()
  const [installedOverride, setInstalledOverride] = useState(false)

  if (localAiAvailable === false && !installedOverride) {
    return <FeatureNotInstalled onInstalled={() => setInstalledOverride(true)} />
  }

  function handleSubmit(numImages: number, ollamaModel: string): void {
    createJob.mutate(
      { num_images: numImages, ollama_model: ollamaModel },
      { onSuccess: (response) => setJobId(response.job_id) }
    )
  }

  const isSubmitting = createJob.isPending || job?.status === 'queued' || job?.status === 'running'
  const result = job?.status === 'succeeded' ? (job.result as BatchJobResult) : null

  return (
    <section className="view">
      <h2>Generar stickers (batch)</h2>
      <BatchForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      {job?.status === 'failed' && <ErrorBanner message={job.error ?? 'Error desconocido'} />}
      <JobProgressPanel jobId={jobId} />
      {result && backendBaseUrl && <ResultsGallery results={result.results} backendBaseUrl={backendBaseUrl} />}
    </section>
  )
}
