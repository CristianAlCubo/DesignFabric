import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Skeleton } from '@/components/ui/skeleton'

import { LogConsole } from '../core/components/LogConsole'
import { useSettingsGeneration } from './SettingsGenerationContext'

export function LocalAiSection() {
  const { readiness, showSkeleton, refreshReadiness } = useSettingsGeneration()
  const [installing, setInstalling] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const available = readiness?.local_ai.available ?? false
  const missing = readiness?.local_ai.missing ?? []

  async function handleInstall(): Promise<void> {
    setInstalling(true)
    setError(null)
    setMessage(null)
    try {
      await window.designfabric.installLocalAiLater()
      setMessage('Módulo de IA local instalado.')
      await refreshReadiness()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo instalar el módulo de IA local.')
    } finally {
      setInstalling(false)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto px-6 py-5">
      <header className="mb-6 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-foreground">IA local</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Módulo de generación local (Ollama + FLUX.2 Klein). Pesa varios GB y requiere descarga
          desde internet.
        </p>
      </header>

      {showSkeleton ? (
        <div className="flex max-w-lg flex-col gap-4" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-40" />
        </div>
      ) : readiness ? (
        <FieldGroup className="max-w-lg gap-4">
          <Field>
            <FieldLabel>Estado</FieldLabel>
            <p className="text-sm text-foreground">
              {available ? 'Instalado' : 'No instalado'}
            </p>
            {!available && missing.length > 0 && (
              <FieldDescription>Falta: {missing.join(', ')}.</FieldDescription>
            )}
          </Field>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={installing || available}
              onClick={() => {
                void handleInstall()
              }}
            >
              {installing ? 'Instalando…' : 'Instalar módulo de IA local'}
            </Button>
          </div>

          {message && <p className="text-sm text-muted-foreground">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}

          {installing && <LogConsole />}
        </FieldGroup>
      ) : null}
    </div>
  )
}
