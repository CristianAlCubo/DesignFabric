import { useState, type CSSProperties } from 'react'

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider
} from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'

import {
  getSettingsSection,
  SETTINGS_SECTIONS,
  type SettingsSectionId
} from './sections'

function SettingsSidebar({
  activeSectionId,
  onSelect
}: {
  activeSectionId: SettingsSectionId
  onSelect: (sectionId: SettingsSectionId) => void
}) {
  return (
    <Sidebar collapsible="none" className="border-r border-sidebar-border">
      <SidebarHeader className="px-4 py-3">
        <span className="text-base font-bold tracking-wide text-sidebar-foreground">
          Configuración
        </span>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {SETTINGS_SECTIONS.map((section) => {
                const selected = section.id === activeSectionId
                const Icon = section.icon
                return (
                  <SidebarMenuItem key={section.id}>
                    <SidebarMenuButton
                      type="button"
                      isActive={selected}
                      size="lg"
                      aria-current={selected ? 'page' : undefined}
                      onClick={() => onSelect(section.id)}
                    >
                      <Icon aria-hidden strokeWidth={1.75} />
                      <span>{section.label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}

function SettingsContent({ sectionId }: { sectionId: SettingsSectionId }) {
  const section = getSettingsSection(sectionId)

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto px-6 py-5">
      <header className="mb-6 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-foreground">{section.label}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{section.description}</p>
      </header>
      <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-border px-6 py-12 text-sm text-muted-foreground">
        Próximamente
      </div>
    </div>
  )
}

export default function SettingsApp() {
  const [activeSectionId, setActiveSectionId] = useState<SettingsSectionId>(
    SETTINGS_SECTIONS[0].id
  )

  return (
    <div className="h-full">
      <TooltipProvider>
        <SidebarProvider
          defaultOpen
          className="h-full! min-h-0!"
          style={
            {
              '--sidebar-width': '13.5rem'
            } as CSSProperties
          }
        >
          <SettingsSidebar activeSectionId={activeSectionId} onSelect={setActiveSectionId} />
          <SidebarInset className="min-h-0 overflow-hidden">
            <SettingsContent sectionId={activeSectionId} />
          </SidebarInset>
        </SidebarProvider>
      </TooltipProvider>
    </div>
  )
}
