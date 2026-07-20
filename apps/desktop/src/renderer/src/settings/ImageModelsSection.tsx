import { useEffect, useState } from 'react'

import type { GenerationPreferences, OpenRouterPublicStatus } from '@shared/generationPreferences'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useGenerationReadiness } from '@/core/hooks/useGenerationReadiness'

import { ModelSearchSelect } from './ModelSearchSelect'
import { ProviderAvailabilityWarning } from './ProviderAvailabilityWarning'
import type { SettingsSectionId } from './sections'

interface ImageModelsSectionProps {
  onNavigate: (sectionId: SettingsSectionId) => void
}

type ImageSettingsTab = 'flux' | 'openrouter' | 'test'

const tabTriggerClassName =
  'h-9 flex-none rounded-none border-0 bg-transparent px-3 py-0 text-sm font-normal text-muted-foreground/80 shadow-none data-active:bg-transparent data-active:font-medium data-active:text-foreground after:bg-primary after:h-0.5 after:opacity-0 group-data-[variant=line]/tabs-list:data-active:after:opacity-100'

function fluxWarningMessages(args: {
  localAiMissing: boolean
  canUseFlux: boolean
  cudaAvailable: boolean
  weightsPresent: boolean
  modelId: string
  missingModules: string[]
}): string[] {
  if (args.canUseFlux) return []
  const messages: string[] = []
  if (args.localAiMissing) {
    messages.push(
      `Requiere el extra local-ai (falta: ${args.missingModules.join(', ') || 'deps'}).`
    )
    return messages
  }
  if (!args.cudaAvailable) {
    messages.push('FLUX.2 Klein requiere CUDA; no hay GPU disponible.')
  }
  if (!args.weightsPresent) {
    messages.push(`Pesos de FLUX no encontrados en caché (${args.modelId}).`)
  }
  if (messages.length === 0) {
    messages.push('El provider FLUX no está listo.')
  }
  return messages
}

function openRouterImageWarningMessages(
  configured: boolean,
  imageModelId: string | null
): string[] {
  const messages: string[] = []
  if (!configured) {
    messages.push('Falta la API key de OpenRouter. Configúrala en la sección OpenRouter.')
  } else if (!imageModelId) {
    messages.push('Selecciona un modelo de imagen para poder usar este provider.')
  }
  return messages
}

export function ImageModelsSection({ onNavigate }: ImageModelsSectionProps) {
  const { readiness, localAiMissing, canUseFlux } = useGenerationReadiness()
  const [prefs, setPrefs] = useState<GenerationPreferences | null>(null)
  const [status, setStatus] = useState<OpenRouterPublicStatus | null>(null)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<ImageSettingsTab>('openrouter')

  useEffect(() => {
    void Promise.all([
      window.designfabric.getGenerationPreferences(),
      window.designfabric.getOpenRouterStatus()
    ]).then(([generationPrefs, openRouterStatus]) => {
      setPrefs(generationPrefs)
      setStatus(openRouterStatus)
    })
  }, [])

  async function updateImageModel(modelId: string | null): Promise<void> {
    if (!prefs) return
    setSaving(true)
    try {
      const next: GenerationPreferences = {
        ...prefs,
        openrouter: { ...prefs.openrouter, imageModelId: modelId }
      }
      const saved = await window.designfabric.setGenerationPreferences(next)
      setPrefs(saved)
    } finally {
      setSaving(false)
    }
  }

  const fluxMessages = fluxWarningMessages({
    localAiMissing,
    canUseFlux,
    cudaAvailable: readiness?.cuda.available ?? false,
    weightsPresent: readiness?.flux.weights_present ?? false,
    modelId: readiness?.flux.model_id ?? 'black-forest-labs/FLUX.2-klein-4B',
    missingModules: readiness?.local_ai.missing ?? []
  })
  const openRouterMessages = openRouterImageWarningMessages(
    status?.configured ?? false,
    prefs?.openrouter.imageModelId ?? readiness?.openrouter?.image_model_id ?? null
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto px-6 py-5">
      <header className="mb-5 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-foreground">Modelos de imagen</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura cada provider de imagen. Un tab por provider.
        </p>
      </header>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as ImageSettingsTab)}
        className="flex min-h-0 flex-1 flex-col gap-4"
        aria-label="Providers de imagen"
      >
        <TabsList
          variant="line"
          className="h-auto w-fit justify-start gap-0 rounded-none bg-transparent p-0"
        >
          <TabsTrigger value="openrouter" className={tabTriggerClassName}>
            OpenRouter
          </TabsTrigger>
          <TabsTrigger value="flux" className={tabTriggerClassName}>
            FLUX.2 Klein
          </TabsTrigger>
          <TabsTrigger value="test" className={tabTriggerClassName}>
            Test
          </TabsTrigger>
        </TabsList>

        <TabsContent value="flux" className="mt-0 flex max-w-xl flex-col gap-4">
          <ProviderAvailabilityWarning messages={fluxMessages} />
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>
              Provider local de imagen (diffusers). El modelo está fijado en la app; no requiere
              selector adicional.
            </p>
            {readiness && (
              <div className="rounded-lg border border-border px-3 py-2 text-foreground">
                <p>
                  Modelo:{' '}
                  <span className="font-mono text-xs">{readiness.flux.model_id}</span>
                </p>
                <p className="mt-1">
                  Pesos en caché: {readiness.flux.weights_present ? 'sí' : 'no'}
                  {readiness.flux.cache_hint ? ` (${readiness.flux.cache_hint})` : ''}
                </p>
                <p className="mt-1">
                  CUDA: {readiness.cuda.available ? readiness.cuda.device_name ?? 'disponible' : 'no'}
                </p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="openrouter" className="mt-0 flex max-w-xl flex-col gap-4">
          <ProviderAvailabilityWarning
            messages={openRouterMessages}
            title={status?.configured ? 'Configuración incompleta' : 'Provider no disponible'}
          />
          <p className="text-sm text-muted-foreground">
            Modelo usado cuando eliges OpenRouter como provider de imagen en generación.
          </p>
          <ModelSearchSelect
            modality="image"
            value={prefs?.openrouter.imageModelId ?? null}
            onChange={(id) => {
              void updateImageModel(id)
            }}
            disabled={saving || !prefs}
            configured={status?.configured ?? false}
            onGoToOpenRouter={() => onNavigate('openrouter')}
          />
        </TabsContent>

        <TabsContent value="test" className="mt-0 flex max-w-xl flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            Stub de desarrollo: siempre disponible. Copia un PNG fijo empaquetado, sin GPU ni
            servicios externos.
          </p>
          <div className="rounded-lg border border-border px-3 py-2 text-sm text-foreground">
            Estado: disponible
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
