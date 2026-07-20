import { useEffect, useState, type FormEvent } from 'react'
import { Sparkles } from 'lucide-react'

import { Checkbox } from '@/components/ui/checkbox'
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
import { useGenerationReadiness } from '../../core/hooks/useGenerationReadiness'
import type { ImageProviderId, LlmProviderId } from '../../core/api/types'

import { useGenerationBatchStore } from './store'

interface BatchFormProps {
  onSubmit: () => void
  isSubmitting: boolean
}

const QUANTITY_PRESETS = ['1', '4', '8', '12'] as const

function pickDefault(
  providers: { id: string; available: boolean }[],
  preferred: string,
  fallback: string
): string {
  const preferredItem = providers.find((p) => p.id === preferred && p.available)
  if (preferredItem) return preferredItem.id
  const available = providers.find((p) => p.available)
  return available?.id ?? fallback
}

function useSupportsTransparency(enabled: boolean, imageModelId: string | null): boolean {
  const [supports, setSupports] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setSupports(false)
      return
    }
    let cancelled = false
    void window.designfabric.getGenerationPreferences().then((prefs) => {
      if (!cancelled) setSupports(prefs.openrouter.imageModelSupportsTransparency)
    })
    return () => {
      cancelled = true
    }
  }, [enabled, imageModelId])

  return supports
}

/** Formulario batch: estado en Zustand (sobrevive a la navegación). */
export function BatchForm({ onSubmit, isSubmitting }: BatchFormProps) {
  const { readiness, catalog, canUseOllama, hasOllamaModel, isLlmExecutable, isImageExecutable } =
    useGenerationReadiness()

  const numImages = useGenerationBatchStore((s) => s.numImages)
  const ollamaModel = useGenerationBatchStore((s) => s.ollamaModel)
  const llmProvider = useGenerationBatchStore((s) => s.llmProvider)
  const imageProvider = useGenerationBatchStore((s) => s.imageProvider)
  const transparentBackground = useGenerationBatchStore((s) => s.transparentBackground)
  const setNumImages = useGenerationBatchStore((s) => s.setNumImages)
  const setOllamaModel = useGenerationBatchStore((s) => s.setOllamaModel)
  const setLlmProvider = useGenerationBatchStore((s) => s.setLlmProvider)
  const setImageProvider = useGenerationBatchStore((s) => s.setImageProvider)
  const setTransparentBackground = useGenerationBatchStore((s) => s.setTransparentBackground)
  const ensureProviderDefaults = useGenerationBatchStore((s) => s.ensureProviderDefaults)
  const ensureOllamaModel = useGenerationBatchStore((s) => s.ensureOllamaModel)

  useEffect(() => {
    if (!catalog) return
    ensureProviderDefaults(
      pickDefault(catalog.llm, 'ollama', 'test') as LlmProviderId,
      pickDefault(catalog.image, 'flux', 'test') as ImageProviderId
    )
  }, [catalog, ensureProviderDefaults])

  useEffect(() => {
    ensureOllamaModel(readiness?.ollama.models ?? [])
  }, [readiness, ensureOllamaModel])

  const showTransparentOption =
    imageProvider === 'openrouter' && Boolean(readiness?.openrouter?.image_model_id)
  const supportsTransparency = useSupportsTransparency(
    showTransparentOption,
    readiness?.openrouter?.image_model_id ?? null
  )

  const modelOk = llmProvider !== 'ollama' || hasOllamaModel(ollamaModel)
  const comboOk =
    isLlmExecutable(llmProvider, ollamaModel) && isImageExecutable(imageProvider) && modelOk

  const canSubmit = Boolean(catalog) && !isSubmitting && comboOk

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    if (!canSubmit) return
    onSubmit()
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

        {showTransparentOption && supportsTransparency ? (
          <Field orientation="horizontal">
            <Checkbox
              id="batch-transparent-background"
              checked={transparentBackground}
              onCheckedChange={(checked) => setTransparentBackground(checked === true)}
            />
            <div className="flex flex-col gap-0.5">
              <FieldLabel htmlFor="batch-transparent-background">Fondo transparente</FieldLabel>
              <FieldDescription>
                Pide transparencia nativa al modelo (PNG con alpha).
              </FieldDescription>
            </div>
          </Field>
        ) : null}

        <FieldSeparator>Configuración</FieldSeparator>

        <ProviderSelector
          label="Provider LLM"
          value={llmProvider}
          providers={llmProviders}
          onChange={(v) => setLlmProvider(v as LlmProviderId)}
          disabled={!catalog || isSubmitting}
        />
        {llmProvider === 'ollama' && (
          <ModelSelector
            value={ollamaModel}
            onChange={setOllamaModel}
            models={readiness?.ollama.models ?? []}
            disabled={isSubmitting || !canUseOllama}
            modelMissing={!modelOk}
          />
        )}
        <ProviderSelector
          label="Provider de imagen"
          value={imageProvider}
          providers={imageProviders}
          onChange={(v) => setImageProvider(v as ImageProviderId)}
          disabled={!catalog || isSubmitting}
        />
      </FieldGroup>

      <AppButton type="submit" size="lg" className="w-full" icon={Sparkles} disabled={!canSubmit}>
        {isSubmitting ? 'Generando…' : 'Generar'}
      </AppButton>
    </form>
  )
}
