/**
 * Placeholder mostrado en las vistas que dependen de IA local
 * (`BatchGeneratorView`, `SingleImageView`) cuando `/features` reporta que el
 * extra `local-ai` no está instalado. Deja instalarlo ahí mismo — el mismo
 * flujo "instalar más tarde" del wizard, disparado desde IPC
 * `setup:install-local-ai-later`.
 */

import { useState } from 'react'

import { LogConsole } from './LogConsole'

interface FeatureNotInstalledProps {
  onInstalled: () => void
}

export function FeatureNotInstalled({ onInstalled }: FeatureNotInstalledProps) {
  const [installing, setInstalling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleInstall(): Promise<void> {
    setInstalling(true)
    setError(null)
    try {
      await window.designfabric.installLocalAiLater()
      onInstalled()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo instalar el módulo de IA local.')
    } finally {
      setInstalling(false)
    }
  }

  return (
    <div className="feature-not-installed">
      <p>
        Este módulo requiere instalar el entorno de generación por IA local (varios GB, requiere
        internet).
      </p>
      <button type="button" className="btn btn--primary" disabled={installing} onClick={() => void handleInstall()}>
        {installing ? 'Instalando…' : 'Instalar ahora'}
      </button>
      {installing ? <LogConsole /> : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
