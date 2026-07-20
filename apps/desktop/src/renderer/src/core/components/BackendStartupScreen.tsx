/**
 * Pantalla de arranque a pantalla completa mientras el backend local
 * (`uvicorn`) aún no responde en `/health`. Sustituye los "Cargando…"
 * locales de cada panel.
 */

import { LoaderCircle, RotateCw } from 'lucide-react'

import { AppButton } from './AppButton'

interface BackendStartupScreenProps {
  error?: string | null
  onRetry?: () => void
}

export function BackendStartupScreen({ error = null, onRetry }: BackendStartupScreenProps) {
  return (
    <div className="wizard-overlay" role="status" aria-live="polite">
      <div className="wizard-card items-center text-center">
        <p className="text-base font-bold tracking-wide">DesignFabric</p>
        {error ? (
          <>
            <p className="error" role="alert">
              {error}
            </p>
            {onRetry ? (
              <AppButton type="button" icon={RotateCw} onClick={onRetry}>
                Reintentar
              </AppButton>
            ) : null}
          </>
        ) : (
          <>
            <LoaderCircle className="size-8 animate-spin text-muted-foreground" aria-hidden />
            <p className="muted">Iniciando servicios…</p>
          </>
        )}
      </div>
    </div>
  )
}
