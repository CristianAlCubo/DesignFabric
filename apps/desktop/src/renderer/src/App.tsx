import { QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import type { SetupPreferences } from '@shared/setupPreferences'

import './features' // side-effect: cada feature se auto-registra al importarse (Fase 6)
import { LogConsole } from './core/components/LogConsole'
import { SetupWizard } from './core/components/SetupWizard'
import { TabPane } from './core/components/TabPane'
import { featureRegistry } from './core/registry/featureRegistry'
import { useNavigationStore } from './core/state/navigationStore'
import { queryClient } from './core/state/queryClient'

function AppShell() {
  const tabs = featureRegistry.list()
  const activeId = useNavigationStore((state) => state.activeTabId)
  const setActiveId = useNavigationStore((state) => state.setActiveTab)
  // Visible por defecto: en el primer arranque de una build empaquetada, el
  // setup del entorno Python (torch/diffusers) puede tardar varios minutos y
  // requiere internet — mostrar la consola de entrada ayuda a notar el
  // progreso. El usuario puede colapsarla después.
  const [showLogs, setShowLogs] = useState(true)

  // Selecciona la primera tab por defecto una vez que el registro de features
  // terminó de poblarse (import de `./features` de arriba, side-effect).
  useEffect(() => {
    if (activeId === null && tabs[0]) setActiveId(tabs[0].id)
  }, [activeId, tabs, setActiveId])

  const activeTab = tabs.find((tab) => tab.id === activeId)
  const ActivePanel = activeTab?.Panel

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__brand">DesignFabricV2</h1>
        <button
          type="button"
          className="logs-toggle"
          onClick={() => setShowLogs((value) => !value)}
        >
          {showLogs ? 'Ocultar registro' : 'Mostrar registro'}
        </button>
      </header>
      <div className="app__tabs">
        <TabPane tabs={tabs} activeId={activeId ?? ''} onChange={setActiveId} />
      </div>
      <main className="page">{ActivePanel ? <ActivePanel /> : null}</main>
      {showLogs ? <LogConsole /> : null}
    </div>
  )
}

/**
 * Gatea `AppShell` detrás del wizard de primer arranque. En dev, el handler
 * `setup:get-preferences` (ver `main/setup-ipc.ts`) reporta siempre
 * "completado" sin tocar disco, así que acá nunca se ve el wizard mientras
 * se desarrolla — solo aplica a builds empaquetadas sin preferencias previas.
 */
function AppGate() {
  const [prefs, setPrefs] = useState<SetupPreferences | null>(null)

  useEffect(() => {
    window.designfabricv2.getSetupPreferences().then(setPrefs)
  }, [])

  if (prefs === null) return null
  if (!prefs.wizardCompleted) return <SetupWizard onCompleted={setPrefs} />
  return <AppShell />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppGate />
    </QueryClientProvider>
  )
}
