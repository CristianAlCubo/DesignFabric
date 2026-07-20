import { useEffect, useState } from 'react'

import type { GenerationPreferences, OpenRouterPublicStatus } from '@shared/generationPreferences'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useGenerationReadiness } from '@/core/hooks/useGenerationReadiness'

import { ModelSearchSelect } from './ModelSearchSelect'
import { ProviderAvailabilityWarning } from './ProviderAvailabilityWarning'
import type { SettingsSectionId } from './sections'

interface LanguageModelsSectionProps {
  onNavigate: (sectionId: SettingsSectionId) => void
}

type LlmSettingsTab = 'ollama' | 'openrouter' | 'test'

const tabTriggerClassName =
  'h-9 flex-none rounded-none border-0 bg-transparent px-3 py-0 text-sm font-normal text-muted-foreground/80 shadow-none data-active:bg-transparent data-active:font-medium data-active:text-foreground after:bg-primary after:h-0.5 after:opacity-0 group-data-[variant=line]/tabs-list:data-active:after:opacity-100'

function ollamaWarningMessages(args: {
  localAiMissing: boolean
  canUseOllama: boolean
  host: string
  error: string | null
  missingModules: string[]
}): string[] {
  if (args.canUseOllama) return []
  const messages: string[] = []
  if (args.localAiMissing) {
    messages.push(
      `Requiere el extra local-ai (falta: ${args.missingModules.join(', ') || 'deps'}).`
    )
  } else if (args.error) {
    messages.push(`Ollama no responde en ${args.host}: ${args.error}`)
  } else {
    messages.push(`Ollama no responde en ${args.host}.`)
  }
  return messages
}

function openRouterLlmWarningMessages(configured: boolean, textModelId: string | null): string[] {
  const messages: string[] = []
  if (!configured) {
    messages.push('Falta la API key de OpenRouter. Configúrala en la sección OpenRouter.')
  } else if (!textModelId) {
    messages.push('Selecciona un modelo de lenguaje para poder usar este provider.')
  }
  return messages
}

export function LanguageModelsSection({ onNavigate }: LanguageModelsSectionProps) {
  const {
    readiness,
    localAiMissing,
    canUseOllama
  } = useGenerationReadiness()
  const [prefs, setPrefs] = useState<GenerationPreferences | null>(null)
  const [status, setStatus] = useState<OpenRouterPublicStatus | null>(null)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<LlmSettingsTab>('openrouter')

  useEffect(() => {
    void Promise.all([
      window.designfabric.getGenerationPreferences(),
      window.designfabric.getOpenRouterStatus()
    ]).then(([generationPrefs, openRouterStatus]) => {
      setPrefs(generationPrefs)
      setStatus(openRouterStatus)
    })
  }, [])

  async function updateTextModel(modelId: string | null): Promise<void> {
    if (!prefs) return
    setSaving(true)
    try {
      const next: GenerationPreferences = {
        ...prefs,
        openrouter: { ...prefs.openrouter, textModelId: modelId }
      }
      const saved = await window.designfabric.setGenerationPreferences(next)
      setPrefs(saved)
    } finally {
      setSaving(false)
    }
  }

  const ollamaMessages = ollamaWarningMessages({
    localAiMissing,
    canUseOllama,
    host: readiness?.ollama.host ?? 'http://localhost:11434',
    error: readiness?.ollama.error ?? null,
    missingModules: readiness?.local_ai.missing ?? []
  })
  const openRouterMessages = openRouterLlmWarningMessages(
    status?.configured ?? false,
    prefs?.openrouter.textModelId ?? readiness?.openrouter?.text_model_id ?? null
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto px-6 py-5">
      <header className="mb-5 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-foreground">Modelos de lenguaje</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura cada provider de texto. Un tab por provider.
        </p>
      </header>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as LlmSettingsTab)}
        className="flex min-h-0 flex-1 flex-col gap-4"
        aria-label="Providers de lenguaje"
      >
        <TabsList
          variant="line"
          className="h-auto w-fit justify-start gap-0 rounded-none bg-transparent p-0"
        >
          <TabsTrigger value="openrouter" className={tabTriggerClassName}>
            OpenRouter
          </TabsTrigger>
          <TabsTrigger value="ollama" className={tabTriggerClassName}>
            Ollama
          </TabsTrigger>
          <TabsTrigger value="test" className={tabTriggerClassName}>
            Test
          </TabsTrigger>
        </TabsList>

        <TabsContent value="ollama" className="mt-0 flex max-w-xl flex-col gap-4">
          <ProviderAvailabilityWarning messages={ollamaMessages} />
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>
              Provider local vía Ollama. El modelo concreto se elige en el formulario de generación
              batch (lista de modelos instalados en el daemon).
            </p>
            {canUseOllama && readiness && (
              <div className="rounded-lg border border-border px-3 py-2">
                <p className="text-foreground">
                  Host: <span className="font-mono text-xs">{readiness.ollama.host}</span>
                </p>
                <p className="mt-1">
                  Modelos instalados:{' '}
                  {readiness.ollama.models.length > 0
                    ? readiness.ollama.models.join(', ')
                    : '(ninguno)'}
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
            Modelo usado cuando eliges OpenRouter como provider LLM en generación.
          </p>
          <ModelSearchSelect
            modality="text"
            value={prefs?.openrouter.textModelId ?? null}
            onChange={(id) => {
              void updateTextModel(id)
            }}
            disabled={saving || !prefs}
            configured={status?.configured ?? false}
            onGoToOpenRouter={() => onNavigate('openrouter')}
          />
        </TabsContent>

        <TabsContent value="test" className="mt-0 flex max-w-xl flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            Stub de desarrollo: siempre disponible. Devuelve un texto fijo para conceptos, sin
            llamar a ningún servicio externo ni a Ollama.
          </p>
          <div className="rounded-lg border border-border px-3 py-2 text-sm text-foreground">
            Estado: disponible
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
