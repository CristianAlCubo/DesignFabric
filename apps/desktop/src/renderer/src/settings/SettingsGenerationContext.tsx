import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from 'react'

import type {
  GenerationPreferences,
  OpenRouterPublicStatus
} from '@shared/generationPreferences'

import { apiGet } from '@/core/api/httpClient'
import type { GenerationReadiness } from '@/core/api/types'

import { useDeferredLoading } from './useDeferredLoading'

interface SettingsGenerationContextValue {
  prefs: GenerationPreferences | null
  status: OpenRouterPublicStatus | null
  readiness: GenerationReadiness | null
  /** true solo si la hidratación inicial aún no terminó */
  hydrating: boolean
  /** skeleton diferido: solo tras umbral, evita flash en cargas rápidas */
  showSkeleton: boolean
  setPrefs: (prefs: GenerationPreferences) => void
  setStatus: (status: OpenRouterPublicStatus) => void
  refreshReadiness: () => Promise<void>
}

const SettingsGenerationContext = createContext<SettingsGenerationContextValue | null>(null)

/**
 * Hidrata una sola vez prefs/status/readiness para toda la ventana Settings.
 * Evita re-fetch + skeleton al cambiar de sección (lifted state + shared cache).
 */
export function SettingsGenerationProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<GenerationPreferences | null>(null)
  const [status, setStatus] = useState<OpenRouterPublicStatus | null>(null)
  const [readiness, setReadiness] = useState<GenerationReadiness | null>(null)
  const [hydrating, setHydrating] = useState(true)

  const refreshReadiness = useCallback(async () => {
    try {
      const res = await apiGet<GenerationReadiness>('/api/generation/readiness')
      setReadiness(res)
    } catch {
      // Mantener último readiness conocido; no forzar fallback que dispare warnings.
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const [generationPrefs, openRouterStatus, ready] = await Promise.all([
          window.designfabric.getGenerationPreferences(),
          window.designfabric.getOpenRouterStatus(),
          apiGet<GenerationReadiness>('/api/generation/readiness').catch(() => null)
        ])
        if (cancelled) return
        setPrefs(generationPrefs)
        setStatus(openRouterStatus)
        if (ready) setReadiness(ready)
      } finally {
        if (!cancelled) setHydrating(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const showSkeleton = useDeferredLoading(hydrating, 200)

  const value = useMemo(
    () => ({
      prefs,
      status,
      readiness,
      hydrating,
      showSkeleton,
      setPrefs,
      setStatus,
      refreshReadiness
    }),
    [prefs, status, readiness, hydrating, showSkeleton, refreshReadiness]
  )

  return (
    <SettingsGenerationContext.Provider value={value}>{children}</SettingsGenerationContext.Provider>
  )
}

export function useSettingsGeneration(): SettingsGenerationContextValue {
  const ctx = useContext(SettingsGenerationContext)
  if (!ctx) {
    throw new Error('useSettingsGeneration debe usarse dentro de SettingsGenerationProvider')
  }
  return ctx
}
