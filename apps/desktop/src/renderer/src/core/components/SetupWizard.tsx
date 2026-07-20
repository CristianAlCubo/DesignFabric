/**
 * Wizard de primer arranque: se muestra antes del shell normal cuando
 * `getSetupPreferences()` reporta `wizardCompleted: false` (empaquetado, sin
 * preferencias previas). Deja elegir si instalar el módulo de IA local
 * (Ollama + FLUX.2) de inmediato o más tarde; en cualquier caso, la promesa
 * de `completeWizard` no resuelve hasta que el backend correspondiente esté
 * arriba, por eso se monta `LogConsole` para ver el progreso real.
 */

import { useState } from 'react'
import { Clock, Download } from 'lucide-react'

import type { SetupPreferences } from '@shared/setupPreferences'

import { AppButton } from './AppButton'
import { LogConsole } from './LogConsole'

interface SetupWizardProps {
  onCompleted: (prefs: SetupPreferences) => void
}

export function SetupWizard({ onCompleted }: SetupWizardProps) {
  const [choice, setChoice] = useState<'installed' | 'deferred' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const busy = choice !== null && error === null

  async function handleChoice(value: 'installed' | 'deferred'): Promise<void> {
    setChoice(value)
    setError(null)
    try {
      const prefs = await window.designfabric.completeWizard(value)
      onCompleted(prefs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo completar la configuración.')
    }
  }

  return (
    <div className="wizard-overlay">
      <div className="wizard-card">
        <h1>Bienvenido a DesignFabric</h1>
        <p>
          Esta app incluye generación de imágenes con IA local (Ollama + FLUX.2). Ese módulo pesa
          varios GB y requiere descarga desde internet.
        </p>
        <p>¿Querés instalarlo ahora, o preferís hacerlo más adelante?</p>
        <div className="flex flex-wrap gap-3">
          <AppButton
            type="button"
            icon={Download}
            disabled={busy}
            onClick={() => void handleChoice('installed')}
          >
            Instalar ahora
          </AppButton>
          <AppButton
            type="button"
            variant="ghost"
            icon={Clock}
            disabled={busy}
            onClick={() => void handleChoice('deferred')}
          >
            Más tarde
          </AppButton>
        </div>
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
        {choice === 'installed' && !error ? (
          <div className="wizard-card__progress">
            <p>Configurando el entorno de IA — esto puede tardar varios minutos…</p>
            <LogConsole />
          </div>
        ) : null}
      </div>
    </div>
  )
}
