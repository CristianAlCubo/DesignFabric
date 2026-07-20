import { useEffect, useState } from 'react'
import { Pencil, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

import { apiGet } from '@/core/api/httpClient'

interface OpenRouterModelRow {
  id: string
  name: string
  output_modalities: string[]
}

interface OpenRouterModelsResponse {
  models: OpenRouterModelRow[]
}

interface ModelSearchSelectProps {
  modality: 'text' | 'image'
  value: string | null
  onChange: (modelId: string | null) => void
  disabled?: boolean
  configured: boolean
  onGoToOpenRouter?: () => void
}

const DEBOUNCE_MS = 300

/** Selector de modelos OpenRouter: selección compacta o buscador (no ambos a la vez). */
export function ModelSearchSelect({
  modality,
  value,
  onChange,
  disabled,
  configured,
  onGoToOpenRouter
}: ModelSearchSelectProps) {
  const [browsing, setBrowsing] = useState(!value)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [models, setModels] = useState<OpenRouterModelRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedMeta, setSelectedMeta] = useState<{ id: string; name: string } | null>(
    value ? { id: value, name: value } : null
  )

  useEffect(() => {
    if (!value) {
      setSelectedMeta(null)
      setBrowsing(true)
      return
    }
    setSelectedMeta((prev) => (prev?.id === value ? prev : { id: value, name: value }))
    setBrowsing(false)
  }, [value])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!configured || !browsing) {
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    const params = new URLSearchParams({ modality })
    if (debouncedQuery.trim()) params.set('q', debouncedQuery.trim())

    void apiGet<OpenRouterModelsResponse>(`/api/openrouter/models?${params.toString()}`)
      .then((res) => {
        if (cancelled) return
        setModels(res.models)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setModels([])
        setError(err instanceof Error ? err.message : 'No se pudieron cargar los modelos.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [configured, modality, debouncedQuery, browsing])

  function clearSearchState(): void {
    setQuery('')
    setDebouncedQuery('')
    setModels([])
    setError(null)
  }

  function handleSelect(model: OpenRouterModelRow): void {
    setSelectedMeta({ id: model.id, name: model.name })
    clearSearchState()
    setBrowsing(false)
    onChange(model.id)
  }

  function handleClear(): void {
    setSelectedMeta(null)
    clearSearchState()
    setBrowsing(true)
    onChange(null)
  }

  function handleChange(): void {
    clearSearchState()
    setBrowsing(true)
  }

  if (!configured) {
    return (
      <div className="rounded-lg border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
        <p>Configura primero la API key de OpenRouter.</p>
        {onGoToOpenRouter && (
          <Button type="button" variant="outline" size="sm" className="mt-3" onClick={onGoToOpenRouter}>
            Ir a OpenRouter
          </Button>
        )}
      </div>
    )
  }

  if (value && !browsing) {
    const displayName = selectedMeta?.id === value ? selectedMeta.name : value
    const showIdAside = displayName !== value

    return (
      <div className="flex items-start justify-between gap-3 rounded-lg border border-border bg-muted/20 px-3 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">{displayName}</p>
          {showIdAside ? (
            <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">{value}</p>
          ) : (
            <p className="mt-0.5 text-xs text-muted-foreground">Modelo seleccionado</p>
          )}
        </div>
        <div className="flex shrink-0 gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled}
            onClick={handleChange}
            aria-label="Cambiar modelo"
          >
            <Pencil aria-hidden />
            Cambiar
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled}
            onClick={handleClear}
            aria-label="Quitar modelo"
          >
            <X aria-hidden />
            Quitar
          </Button>
        </div>
      </div>
    )
  }

  const visibleModels = value ? models.filter((model) => model.id !== value) : models

  return (
    <div className="flex flex-col gap-3">
      {value && (
        <p className="text-xs text-muted-foreground">
          Eligiendo reemplazo de <span className="font-mono text-foreground">{value}</span>
        </p>
      )}

      <Input
        type="search"
        placeholder="Buscar modelos…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={disabled}
        aria-label="Filtrar modelos OpenRouter"
        aria-busy={loading}
        autoFocus
      />

      {value && (
        <div className="flex justify-end">
          <Button type="button" variant="ghost" size="sm" disabled={disabled} onClick={() => setBrowsing(false)}>
            Cancelar
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando modelos…</p>}

      {!loading && !error && visibleModels.length === 0 && (
        <p className="text-sm text-muted-foreground">Sin resultados.</p>
      )}

      {visibleModels.length > 0 && (
        <ul className="max-h-64 overflow-auto rounded-lg border border-border">
          {visibleModels.map((model) => (
            <li key={model.id}>
              <button
                type="button"
                disabled={disabled}
                className={cn(
                  'flex w-full flex-col items-start gap-0.5 border-b border-border px-3 py-2 text-left text-sm last:border-b-0 hover:bg-muted/50'
                )}
                onClick={() => handleSelect(model)}
              >
                <span className="text-foreground">{model.name}</span>
                <span className="font-mono text-xs text-muted-foreground">{model.id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
