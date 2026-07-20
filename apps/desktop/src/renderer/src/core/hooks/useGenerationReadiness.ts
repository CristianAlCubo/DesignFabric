import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiGet } from '../api/httpClient'
import type { GenerationProvidersResponse, GenerationReadiness, ProviderInfo } from '../api/types'

const FALLBACK_READINESS: GenerationReadiness = {
  local_ai: { available: false, missing: ['torch', 'diffusers', 'ollama', 'langchain_ollama'] },
  ollama: { host: 'http://localhost:11434', reachable: false, models: [], error: 'No se pudo consultar readiness' },
  flux: { model_id: 'black-forest-labs/FLUX.2-klein-4B', weights_present: false, cache_hint: null },
  cuda: { available: false, device_name: null },
  providers: { ollama: false, flux: false, test_llm: true, test_image: true }
}

function providersFromReadiness(ready: GenerationReadiness): GenerationProvidersResponse {
  const llm: ProviderInfo[] = [
    {
      id: 'ollama',
      label: 'Ollama',
      available: ready.providers.ollama,
      requires_local_ai: true
    },
    {
      id: 'test',
      label: 'Test (texto fijo)',
      available: ready.providers.test_llm,
      requires_local_ai: false
    }
  ]
  const image: ProviderInfo[] = [
    {
      id: 'flux',
      label: 'FLUX.2 Klein',
      available: ready.providers.flux,
      requires_local_ai: true
    },
    {
      id: 'test',
      label: 'Test (imagen fija)',
      available: ready.providers.test_image,
      requires_local_ai: false
    }
  ]
  return { llm, image }
}

function hasOllamaModel(ready: GenerationReadiness, model: string): boolean {
  if (!model || !ready.ollama.reachable) return false
  if (ready.ollama.models.includes(model)) return true
  return ready.ollama.models.some((m) => m === model || m.startsWith(`${model}:`))
}

export interface GenerationReadinessState {
  readiness: GenerationReadiness | null
  catalog: GenerationProvidersResponse | null
  loading: boolean
  refresh: () => Promise<void>
  localAiMissing: boolean
  canUseOllama: boolean
  canUseFlux: boolean
  hasOllamaModel: (model: string) => boolean
  statusMessages: string[]
}

/** SSOT de readiness de generación IA; un solo fetch para forms y banners. */
export function useGenerationReadiness(): GenerationReadinessState {
  const [readiness, setReadiness] = useState<GenerationReadiness | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiGet<GenerationReadiness>('/api/generation/readiness')
      setReadiness(res)
    } catch {
      setReadiness(FALLBACK_READINESS)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const catalog = useMemo(
    () => (readiness ? providersFromReadiness(readiness) : null),
    [readiness]
  )

  const statusMessages = useMemo(() => {
    if (!readiness) return []
    const messages: string[] = []
    if (!readiness.local_ai.available) {
      messages.push(
        `Extra local-ai no instalado (falta: ${readiness.local_ai.missing.join(', ') || 'deps'}).`
      )
      return messages
    }
    if (!readiness.ollama.reachable) {
      messages.push(
        readiness.ollama.error
          ? `Ollama no responde en ${readiness.ollama.host}: ${readiness.ollama.error}`
          : `Ollama no responde en ${readiness.ollama.host}.`
      )
    }
    if (!readiness.cuda.available) {
      messages.push('CUDA no disponible; FLUX.2 Klein requiere GPU.')
    }
    if (!readiness.flux.weights_present) {
      messages.push(
        `Pesos de FLUX no encontrados en caché (${readiness.flux.model_id}). ` +
          'La descarga/configuración desde la app llegará en un panel futuro.'
      )
    }
    return messages
  }, [readiness])

  return {
    readiness,
    catalog,
    loading,
    refresh,
    localAiMissing: readiness ? !readiness.local_ai.available : false,
    canUseOllama: readiness?.providers.ollama ?? false,
    canUseFlux: readiness?.providers.flux ?? false,
    hasOllamaModel: (model: string) => (readiness ? hasOllamaModel(readiness, model) : false),
    statusMessages
  }
}
