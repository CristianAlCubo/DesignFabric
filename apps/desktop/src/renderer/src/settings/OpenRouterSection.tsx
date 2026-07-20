import { useEffect, useState } from 'react'

import type { OpenRouterPublicStatus } from '@shared/generationPreferences'

import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

export function OpenRouterSection() {
  const [status, setStatus] = useState<OpenRouterPublicStatus | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void window.designfabric.getOpenRouterStatus().then(setStatus)
  }, [])

  async function handleSave(): Promise<void> {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const next = await window.designfabric.setOpenRouterKey(apiKey)
      setStatus(next)
      setApiKey('')
      setMessage('API key guardada.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar la API key.')
    } finally {
      setSaving(false)
    }
  }

  async function handleClear(): Promise<void> {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const next = await window.designfabric.clearOpenRouterKey()
      setStatus(next)
      setMessage('API key eliminada.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar la API key.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto px-6 py-5">
      <header className="mb-6 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-foreground">OpenRouter</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Una sola API key para providers de texto e imagen.
        </p>
      </header>

      <FieldGroup className="max-w-lg gap-4">
        <Field>
          <FieldLabel>Estado</FieldLabel>
          <p className="text-sm text-foreground">
            {status?.configured
              ? `Configurada (${status.maskedKey ?? '••••'})`
              : 'Sin configurar'}
          </p>
          {status && !status.encryptionAvailable && (
            <FieldDescription className="text-destructive">
              El cifrado seguro no está disponible en este sistema; no se puede guardar la key.
            </FieldDescription>
          )}
        </Field>

        <Field>
          <FieldLabel htmlFor="openrouter-api-key">API key</FieldLabel>
          <Input
            id="openrouter-api-key"
            type="password"
            autoComplete="off"
            placeholder="sk-or-…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            disabled={saving || status?.encryptionAvailable === false}
          />
          <FieldDescription>Se almacena cifrada con safeStorage de Electron.</FieldDescription>
        </Field>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={saving || !apiKey.trim() || status?.encryptionAvailable === false}
            onClick={() => {
              void handleSave()
            }}
          >
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={saving || !status?.configured}
            onClick={() => {
              void handleClear()
            }}
          >
            Eliminar key
          </Button>
        </div>

        {message && <p className="text-sm text-muted-foreground">{message}</p>}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </FieldGroup>
    </div>
  )
}
