import { useEffect, useState } from 'react'

import { apiGet } from '../api/httpClient'
import type { GenerationProvidersResponse } from '../api/types'

/** Catálogo de providers LLM/imagen; `null` mientras carga. */
export function useGenerationProviders(): GenerationProvidersResponse | null {
  const [catalog, setCatalog] = useState<GenerationProvidersResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    apiGet<GenerationProvidersResponse>('/api/generation/providers')
      .then((res) => {
        if (!cancelled) setCatalog(res)
      })
      .catch(() => {
        if (!cancelled) {
          setCatalog({
            llm: [
              { id: 'test', label: 'Test (texto fijo)', available: true, requires_local_ai: false },
              { id: 'ollama', label: 'Ollama', available: false, requires_local_ai: true },
            ],
            image: [
              { id: 'test', label: 'Test (imagen fija)', available: true, requires_local_ai: false },
              { id: 'flux', label: 'FLUX.2 Klein', available: false, requires_local_ai: true },
            ],
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return catalog
}
