import { useEffect, useState } from 'react'

import { apiGet } from '../api/httpClient'

interface FeaturesResponse {
  local_ai_available: boolean
  modules: string[]
}

/** `null` mientras carga, luego `true`/`false` según si el backend reporta el módulo de IA local disponible. */
export function useLocalAiAvailability(): boolean | null {
  const [available, setAvailable] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    apiGet<FeaturesResponse>('/features')
      .then((res) => {
        if (!cancelled) setAvailable(res.local_ai_available)
      })
      .catch(() => {
        if (!cancelled) setAvailable(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return available
}
