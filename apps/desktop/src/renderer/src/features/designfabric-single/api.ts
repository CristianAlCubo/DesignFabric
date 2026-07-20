/**
 * Hooks de React Query específicos del job single-image de DesignFabric: la
 * mutation para encolarlo y la query genérica de estado de un job (usada
 * también, de forma duplicada pero mínima, por `designfabric-batch/api.ts`
 * para mantener cada feature autocontenida).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiGet, apiPost } from '../../core/api/httpClient'
import type { JobCreatedResponse, JobStatusResponse, SingleImageJobRequest } from '../../core/api/types'

const ACTIVE_STATUSES = new Set(['queued', 'running'])

export function useCreateSingleImageJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: SingleImageJobRequest) =>
      apiPost<SingleImageJobRequest, JobCreatedResponse>('/api/jobs/single-image', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] })
  })
}

/** Query genérica de un job por id, con polling mientras esté en curso. */
export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => apiGet<JobStatusResponse>(`/api/jobs/${jobId}`),
    enabled: jobId !== null,
    // Mientras el job sigue en curso, hacemos polling como respaldo del
    // WebSocket de progreso (por si la conexión se cae).
    refetchInterval: (query) => (ACTIVE_STATUSES.has(query.state.data?.status ?? '') ? 1000 : false)
  })
}
