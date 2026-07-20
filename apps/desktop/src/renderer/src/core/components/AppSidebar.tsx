import { Settings } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem
} from '@/components/ui/sidebar'

import { useAppVersion } from '../hooks/useAppVersion'
import { listSections } from '../registry/sections'
import type { SectionId } from '../registry/types'

interface AppSidebarProps {
  activeSectionId: SectionId | null
  onSelect: (sectionId: SectionId) => void
}

export function AppSidebar({ activeSectionId, onSelect }: AppSidebarProps) {
  const sections = listSections()
  const version = useAppVersion()

  return (
    <Sidebar collapsible="none" className="border-r border-sidebar-border">
      <SidebarHeader className="px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-base font-bold tracking-wide text-sidebar-foreground">
            DesignFabric
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Abrir configuración"
            title="Configuración"
            onClick={() => {
              void window.designfabric.openSettings()
            }}
          >
            <Settings aria-hidden strokeWidth={1.75} />
          </Button>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {sections.map((section) => {
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
      <SidebarFooter className="mt-auto border-t border-sidebar-border px-4 py-3">
        <p className="text-xs text-muted-foreground tabular-nums" title="Versión del software">
          {version ? `v${version}` : '…'}
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}
