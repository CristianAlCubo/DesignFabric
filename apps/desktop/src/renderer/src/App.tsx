import { QueryClientProvider } from '@tanstack/react-query'
import { Terminal } from 'lucide-react'
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'

import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'

import './features' // side-effect: cada feature se auto-registra al importarse
import { AppButton } from './core/components/AppButton'
import { AppSidebar } from './core/components/AppSidebar'
import { BackendStartupScreen } from './core/components/BackendStartupScreen'
import { ConsoleSheet } from './core/components/ConsoleSheet'
import { SectionWorkspace } from './core/components/SectionWorkspace'
import { useBackendReady } from './core/hooks/useBackendReady'
import { useNavigationStore } from './core/state/navigationStore'
import { queryClient } from './core/state/queryClient'

function AppShell() {
  const activeTabId = useNavigationStore((state) => state.activeTabId)
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
              '--sidebar-width': '19rem'
            } as CSSProperties
          }
        >
          <AppSidebar activeTabId={activeTabId} onSelectTab={setActiveTab} />
          <SidebarInset className="min-h-0 overflow-hidden">
            <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-5 py-2.5">
              <SidebarTrigger />
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
            <SectionWorkspace activeTabId={activeTabId} />
          </SidebarInset>
          <ConsoleSheet open={showLogs} onClose={() => setShowLogs(false)} />
        </SidebarProvider>
      </TooltipProvider>
    </div>
  )
}

/** Monta el shell solo cuando el backend local responde en `/health`. */
function BackendReadyGate({ children }: { children: ReactNode }) {
  const backend = useBackendReady()

  if (backend.status !== 'ready') {
    return <BackendStartupScreen error={backend.error} onRetry={backend.retry} />
  }
  return children
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BackendReadyGate>
        <AppShell />
      </BackendReadyGate>
    </QueryClientProvider>
  )
}
