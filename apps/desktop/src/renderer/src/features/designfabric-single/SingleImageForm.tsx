import { useEffect, useState, type FormEvent } from 'react'

import { ProviderSelector } from '../../core/components/ProviderSelector'
import { useGenerationProviders } from '../../core/hooks/useGenerationProviders'
import type { ImageProviderId } from '../../core/api/types'

export interface SingleImageFormValues {
  prompt: string
  applyStyleSuffix: boolean
  imageProvider: ImageProviderId
}

interface SingleImageFormProps {
  onSubmit: (values: SingleImageFormValues) => void
  isSubmitting: boolean
}

/** Formulario: prompt libre + provider de imagen. */
export function SingleImageForm({ onSubmit, isSubmitting }: SingleImageFormProps) {
  const catalog = useGenerationProviders()
  const [prompt, setPrompt] = useState('')
  const [applyStyleSuffix, setApplyStyleSuffix] = useState(true)
  const [imageProvider, setImageProvider] = useState<ImageProviderId>('test')

  useEffect(() => {
    if (!catalog) return
    const preferred = catalog.image.find((p) => p.id === 'flux' && p.available)
    const fallback = catalog.image.find((p) => p.available)
    setImageProvider((preferred?.id ?? fallback?.id ?? 'test') as ImageProviderId)
  }, [catalog])

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    const trimmed = prompt.trim()
    if (!trimmed) return
    onSubmit({ prompt: trimmed, applyStyleSuffix, imageProvider })
  }

  return (
    <form className="single-image-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Prompt</span>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="a grumpy owl perched on a stack of old books, wearing tiny reading glasses"
          rows={4}
        />
      </label>
      <ProviderSelector
        label="Provider de imagen"
        value={imageProvider}
        providers={catalog?.image ?? []}
        onChange={(v) => setImageProvider(v as ImageProviderId)}
        disabled={!catalog || isSubmitting}
      />
      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={applyStyleSuffix}
          onChange={(e) => setApplyStyleSuffix(e.target.checked)}
        />
        <span>Aplicar estilo sticker (bordes gruesos, colores planos, fondo blanco)</span>
      </label>
      <button type="submit" disabled={isSubmitting || !prompt.trim() || !catalog}>
        {isSubmitting ? 'Generando…' : 'Generar'}
      </button>
    </form>
  )
}
