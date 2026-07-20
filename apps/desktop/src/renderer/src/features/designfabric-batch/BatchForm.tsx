import { useEffect, useState, type FormEvent } from 'react'
import { Sparkles } from 'lucide-react'

import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSeparator
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
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

const QUANTITY_PRESETS = ['1', '4', '8', '12'] as const

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
  const presetValue = QUANTITY_PRESETS.includes(String(numImages) as (typeof QUANTITY_PRESETS)[number])
    ? String(numImages)
    : ''

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
      <FieldGroup>
        <Field>
          <FieldLabel>Número de stickers</FieldLabel>
          <ToggleGroup
            type="single"
            variant="outline"
            spacing={0}
            className="w-full"
            value={presetValue}
            onValueChange={(value) => {
              if (!value) return
              setNumImages(Number(value))
            }}
            disabled={isSubmitting}
          >
            {QUANTITY_PRESETS.map((preset) => (
              <ToggleGroupItem key={preset} value={preset} className="flex-1">
                {preset}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <div className="flex items-center gap-2">
            <Input
              id="batch-num-images"
              type="number"
              min={1}
              max={50}
              value={numImages}
              onChange={(e) => setNumImages(Number(e.target.value))}
              disabled={isSubmitting}
              className="w-24"
              aria-label="Cantidad personalizada"
            />
            <FieldDescription className="m-0">Hasta 50 por lote.</FieldDescription>
          </div>
        </Field>

        <FieldSeparator>Configuración</FieldSeparator>

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
      </FieldGroup>

      <AppButton
        type="submit"
        size="lg"
        className="w-full"
        icon={Sparkles}
        disabled={isSubmitting || !catalog}
      >
        {isSubmitting ? 'Generando…' : 'Generar'}
      </AppButton>
    </form>
  )
}
