import { useState } from 'react'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { ModelSearchSelect, type OpenRouterModelSelection } from './ModelSearchSelect'
import { ProviderAvailabilityWarning } from './ProviderAvailabilityWarning'
import { useSettingsGeneration } from './SettingsGenerationContext'
import { OpenRouterSettingsSkeleton } from './SettingsSkeletons'
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
  const { prefs, status, readiness, hydrating, showSkeleton, setPrefs, refreshReadiness } =
    useSettingsGeneration()
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<ImageSettingsTab>('openrouter')

  const ready = !hydrating && prefs !== null && status !== null && readiness !== null

  async function updateImageModel(selection: OpenRouterModelSelection | null): Promise<void> {
    if (!prefs) return
    setSaving(true)
    try {
      const next = {
        ...prefs,
        openrouter: {
          ...prefs.openrouter,
          imageModelId: selection?.id ?? null,
          imageModelOutputModalities: selection?.output_modalities ?? null
        }
      }
      const saved = await window.designfabric.setGenerationPreferences(next)
      setPrefs(saved)
      await refreshReadiness()
    } finally {
      setSaving(false)
    }
  }

  const fluxMessages =
    ready && readiness
      ? fluxWarningMessages({
          localAiMissing: !readiness.local_ai.available,
          canUseFlux: readiness.providers.flux,
          cudaAvailable: readiness.cuda.available,
          weightsPresent: readiness.flux.weights_present,
          modelId: readiness.flux.model_id,
          missingModules: readiness.local_ai.missing
        })
      : []

  const openRouterMessages =
    ready && prefs && status
      ? openRouterImageWarningMessages(status.configured, prefs.openrouter.imageModelId)
      : []

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
          {showSkeleton ? (
            <OpenRouterSettingsSkeleton />
          ) : ready && readiness ? (
            <>
              <ProviderAvailabilityWarning messages={fluxMessages} />
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Provider local de imagen (diffusers). El modelo está fijado en la app; no requiere
                  selector adicional.
                </p>
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
                    CUDA:{' '}
                    {readiness.cuda.available ? readiness.cuda.device_name ?? 'disponible' : 'no'}
                  </p>
                </div>
              </div>
            </>
          ) : null}
        </TabsContent>

        <TabsContent value="openrouter" className="mt-0 flex max-w-xl flex-col gap-4">
          {showSkeleton ? (
            <OpenRouterSettingsSkeleton />
          ) : ready && prefs && status ? (
            <>
              <ProviderAvailabilityWarning
                messages={openRouterMessages}
                title={status.configured ? 'Configuración incompleta' : 'Provider no disponible'}
              />
              <p className="text-sm text-muted-foreground">
                Modelo usado cuando eliges OpenRouter como provider de imagen en generación.
              </p>
              <ModelSearchSelect
                modality="image"
                value={prefs.openrouter.imageModelId}
                onChange={(selection) => {
                  void updateImageModel(selection)
                }}
                disabled={saving}
                configured={status.configured}
                onGoToOpenRouter={() => onNavigate('openrouter')}
              />
            </>
          ) : null}
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
