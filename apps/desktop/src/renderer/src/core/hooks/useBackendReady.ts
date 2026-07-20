import { useEffect, useState } from 'react'

import { waitForBackendReady } from '../api/httpClient'

export type BackendReadyStatus = 'waiting' | 'ready' | 'error'

interface BackendReadyState {
  status: BackendReadyStatus
  error: string | null
  retry: () => void
}

/**
 * Espera a que el backend local responda en `/health` antes de montar el shell.
 * `retry` reinicia la espera tras un timeout o fallo.
 */
export function useBackendReady(): BackendReadyState {
  const [status, setStatus] = useState<BackendReadyStatus>('waiting')
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setStatus('waiting')
    setError(null)

    void waitForBackendReady()
      .then(() => {
        if (!cancelled) setStatus('ready')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setStatus('error')
        setError(err instanceof Error ? err.message : 'No se pudo iniciar el backend.')
      })

    return () => {
      cancelled = true
    }
  }, [attempt])

  return {
    status,
    error,
    retry: () => setAttempt((value) => value + 1)
  }
}
