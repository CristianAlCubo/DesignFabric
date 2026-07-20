import { useEffect, useState, type FormEvent } from 'react'

import { ModelSelector } from '../../core/components/ModelSelector'
import { ProviderSelector } from '../../core/components/ProviderSelector'
import { useGenerationProviders } from '../../core/hooks/useGenerationProviders'
import type { ImageProviderId, LlmProviderId } from '../../core/api/types'

export interface BatchFormValues {
  numImages: number
  ollamaModel: string
  llmProvider: LlmProviderId
  imageProvider: ImageProviderId
}

interface BatchFormProps {
  onSubmit: (values: BatchFormValues) => void
  isSubmitting: boolean
}

function pickDefault(providers: { id: string; available: boolean }[], preferred: string, fallback: string): string {
  const preferredItem = providers.find((p) => p.id === preferred && p.available)
  if (preferredItem) return preferredItem.id
  const available = providers.find((p) => p.available)
  return available?.id ?? fallback
}

/** Formulario batch: providers + flags equivalentes al CLI. */
export function BatchForm({ onSubmit, isSubmitting }: BatchFormProps) {
  const catalog = useGenerationProviders()
  const [numImages, setNumImages] = useState(1)
  const [ollamaModel, setOllamaModel] = useState('gemma3:4b')
  const [llmProvider, setLlmProvider] = useState<LlmProviderId>('test')
  const [imageProvider, setImageProvider] = useState<ImageProviderId>('test')

  useEffect(() => {
    if (!catalog) return
    setLlmProvider(pickDefault(catalog.llm, 'ollama', 'test') as LlmProviderId)
    setImageProvider(pickDefault(catalog.image, 'flux', 'test') as ImageProviderId)
  }, [catalog])

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    onSubmit({ numImages, ollamaModel, llmProvider, imageProvider })
  }

  const llmProviders = catalog?.llm ?? []
  const imageProviders = catalog?.image ?? []

  return (
    <form className="batch-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Número de stickers</span>
        <input
          type="number"
          min={1}
          max={50}
          value={numImages}
          onChange={(e) => setNumImages(Number(e.target.value))}
        />
      </label>
      <ProviderSelector
        label="Provider LLM"
        value={llmProvider}
        providers={llmProviders}
        onChange={(v) => setLlmProvider(v as LlmProviderId)}
        disabled={!catalog || isSubmitting}
      />
      {llmProvider === 'ollama' && <ModelSelector value={ollamaModel} onChange={setOllamaModel} />}
      <ProviderSelector
        label="Provider de imagen"
        value={imageProvider}
        providers={imageProviders}
        onChange={(v) => setImageProvider(v as ImageProviderId)}
        disabled={!catalog || isSubmitting}
      />
      <button type="submit" disabled={isSubmitting || !catalog}>
        {isSubmitting ? 'Generando…' : 'Generar'}
      </button>
    </form>
  )
}
