import { QueryClientProvider } from '@tanstack/react-query'
import { Terminal } from 'lucide-react'
import { useEffect, useState, type CSSProperties } from 'react'

import type { SetupPreferences } from '@shared/setupPreferences'

import { Button } from '@/components/ui/button'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'

import './features' // side-effect: cada feature se auto-registra al importarse
import { AppSidebar } from './core/components/AppSidebar'
import { ConsoleSheet } from './core/components/ConsoleSheet'
import { SectionWorkspace } from './core/components/SectionWorkspace'
import { SetupWizard } from './core/components/SetupWizard'
import { useNavigationStore } from './core/state/navigationStore'
import { queryClient } from './core/state/queryClient'

function AppShell() {
  const activeSectionId = useNavigationStore((state) => state.activeSectionId)
  const activeTabId = useNavigationStore((state) => state.activeTabId)
  const setActiveSection = useNavigationStore((state) => state.setActiveSection)
  const setActiveTab = useNavigationStore((state) => state.setActiveTab)
  const ensureDefaults = useNavigationStore((state) => state.ensureDefaults)

  // Visible por defecto: en el primer arranque de una build empaquetada, el
  // setup del entorno Python (torch/diffusers) puede tardar varios minutos y
  // requiere internet — mostrar la consola de entrada ayuda a notar el
  // progreso. El usuario puede colapsarla después.
  const [showLogs, setShowLogs] = useState(true)

  useEffect(() => {
    ensureDefaults()
  }, [ensureDefaults])

  return (
    <div className="h-full">
      <TooltipProvider>
        <SidebarProvider
          defaultOpen
          className="h-full! min-h-0!"
          style={
            {
              '--sidebar-width': '15.5rem'
            } as CSSProperties
          }
        >
          <AppSidebar activeSectionId={activeSectionId} onSelect={setActiveSection} />
          <SidebarInset className="min-h-0 overflow-hidden">
            <header className="flex shrink-0 items-center justify-end gap-3 border-b border-border px-5 py-2.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                aria-expanded={showLogs}
                aria-controls="console-sheet"
                onClick={() => setShowLogs((value) => !value)}
              >
                <Terminal data-icon="inline-start" aria-hidden />
                {showLogs ? 'Ocultar registro' : 'Mostrar registro'}
              </Button>
            </header>
            <SectionWorkspace
              sectionId={activeSectionId}
              activeTabId={activeTabId}
              onTabChange={setActiveTab}
            />
          </SidebarInset>
          <ConsoleSheet open={showLogs} onClose={() => setShowLogs(false)} />
        </SidebarProvider>
      </TooltipProvider>
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
    window.designfabric.getSetupPreferences().then(setPrefs)
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
