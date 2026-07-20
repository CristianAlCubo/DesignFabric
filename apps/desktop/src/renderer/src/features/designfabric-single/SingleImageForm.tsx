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
import { Textarea } from '@/components/ui/textarea'

import { AppButton } from '../../core/components/AppButton'
import { ProviderSelector } from '../../core/components/ProviderSelector'
import { useGenerationReadiness } from '../../core/hooks/useGenerationReadiness'
import type { ImageProviderId } from '../../core/api/types'

import { useGenerationSingleStore } from './store'

interface SingleImageFormProps {
  onSubmit: () => void
  isSubmitting: boolean
}

/** Formulario single: estado en Zustand (sobrevive a la navegación). */
export function SingleImageForm({ onSubmit, isSubmitting }: SingleImageFormProps) {
  const { catalog, isImageExecutable, readiness } = useGenerationReadiness()

  const prompt = useGenerationSingleStore((s) => s.prompt)
  const applyStyleSuffix = useGenerationSingleStore((s) => s.applyStyleSuffix)
  const transparentBackground = useGenerationSingleStore((s) => s.transparentBackground)
  const imageProvider = useGenerationSingleStore((s) => s.imageProvider)
  const setPrompt = useGenerationSingleStore((s) => s.setPrompt)
  const setApplyStyleSuffix = useGenerationSingleStore((s) => s.setApplyStyleSuffix)
  const setTransparentBackground = useGenerationSingleStore((s) => s.setTransparentBackground)
  const setImageProvider = useGenerationSingleStore((s) => s.setImageProvider)
  const ensureImageProviderDefault = useGenerationSingleStore((s) => s.ensureImageProviderDefault)

  useEffect(() => {
    if (!catalog) return
    const preferred = catalog.image.find((p) => p.id === 'flux' && p.available)
    const fallback = catalog.image.find((p) => p.available)
    ensureImageProviderDefault((preferred?.id ?? fallback?.id ?? 'test') as ImageProviderId)
  }, [catalog, ensureImageProviderDefault])

  const showTransparentOption =
    imageProvider === 'openrouter' && Boolean(readiness?.openrouter?.image_model_id)
  const supportsTransparency = useSupportsTransparency(
    showTransparentOption,
    readiness?.openrouter?.image_model_id ?? null
  )

  const comboOk = isImageExecutable(imageProvider)
  const canSubmit = Boolean(catalog) && !isSubmitting && Boolean(prompt.trim()) && comboOk

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    if (!prompt.trim() || !canSubmit) return
    onSubmit()
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="single-prompt">Prompt</FieldLabel>
          <Textarea
            id="single-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="a grumpy owl perched on a stack of old books, wearing tiny reading glasses"
            rows={6}
            className="min-h-32 resize-y"
          />
          <FieldDescription>Describe el sticker que quieres generar.</FieldDescription>
        </Field>

        <Field orientation="horizontal">
          <Checkbox
            id="apply-style-suffix"
            checked={applyStyleSuffix}
            onCheckedChange={(checked) => setApplyStyleSuffix(checked === true)}
          />
          <div className="flex flex-col gap-0.5">
            <FieldLabel htmlFor="apply-style-suffix">Estilo sticker</FieldLabel>
            <FieldDescription>
              Bordes gruesos, colores planos y fondo blanco.
            </FieldDescription>
          </div>
        </Field>

        {showTransparentOption && supportsTransparency ? (
          <Field orientation="horizontal">
            <Checkbox
              id="transparent-background"
              checked={transparentBackground}
              onCheckedChange={(checked) => setTransparentBackground(checked === true)}
            />
            <div className="flex flex-col gap-0.5">
              <FieldLabel htmlFor="transparent-background">Fondo transparente</FieldLabel>
              <FieldDescription>
                Pide transparencia nativa al modelo (PNG con alpha).
              </FieldDescription>
            </div>
          </Field>
        ) : null}

        <FieldSeparator>Configuración</FieldSeparator>

        <ProviderSelector
          label="Provider de imagen"
          value={imageProvider}
          providers={catalog?.image ?? []}
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
