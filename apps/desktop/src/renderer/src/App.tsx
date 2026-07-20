import { QueryClientProvider } from '@tanstack/react-query'
import { Terminal } from 'lucide-react'
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'

import type { SetupPreferences } from '@shared/setupPreferences'

import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'

import './features' // side-effect: cada feature se auto-registra al importarse
import { AppButton } from './core/components/AppButton'
import { AppSidebar } from './core/components/AppSidebar'
import { BackendStartupScreen } from './core/components/BackendStartupScreen'
import { ConsoleSheet } from './core/components/ConsoleSheet'
import { SectionWorkspace } from './core/components/SectionWorkspace'
import { SetupWizard } from './core/components/SetupWizard'
import { useBackendReady } from './core/hooks/useBackendReady'
import { useNavigationStore } from './core/state/navigationStore'
import { queryClient } from './core/state/queryClient'

function AppShell() {
  const activeSectionId = useNavigationStore((state) => state.activeSectionId)
  const activeTabId = useNavigationStore((state) => state.activeTabId)
  const setActiveSection = useNavigationStore((state) => state.setActiveSection)
  const setActiveTab = useNavigationStore((state) => state.setActiveTab)
  const ensureDefaults = useNavigationStore((state) => state.ensureDefaults)

  const [showLogs, setShowLogs] = useState(false)

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
              <AppButton
                type="button"
                variant="outline"
                size="sm"
                icon={Terminal}
                aria-expanded={showLogs}
                aria-controls="console-sheet"
                onClick={() => setShowLogs((value) => !value)}
              >
                {showLogs ? 'Ocultar registro' : 'Mostrar registro'}
              </AppButton>
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
 * Monta el shell solo cuando el backend local responde en `/health`.
 * Se monta después del wizard para no sondear mientras aún no hay proceso.
 */
function BackendReadyGate({ children }: { children: ReactNode }) {
  const backend = useBackendReady()

  if (backend.status !== 'ready') {
    return <BackendStartupScreen error={backend.error} onRetry={backend.retry} />
  }
  return children
}

/**
 * Gatea `AppShell` detrás del wizard de primer arranque y de que el backend
 * local esté listo. En dev, `setup:get-preferences` reporta siempre
 * "completado" sin tocar disco — el wizard solo aplica a builds empaquetadas
 * sin preferencias previas.
 */
function AppGate() {
  const [prefs, setPrefs] = useState<SetupPreferences | null>(null)

  useEffect(() => {
    window.designfabric.getSetupPreferences().then(setPrefs)
  }, [])

  if (prefs === null) return <BackendStartupScreen />
  if (!prefs.wizardCompleted) return <SetupWizard onCompleted={setPrefs} />
  return (
    <BackendReadyGate>
      <AppShell />
    </BackendReadyGate>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppGate />
    </QueryClientProvider>
  )
}
