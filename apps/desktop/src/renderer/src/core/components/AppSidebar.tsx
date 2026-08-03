import { Settings } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem
} from '@/components/ui/sidebar'

import { featureRegistry } from '../registry/featureRegistry'
import { useAppVersion } from '../hooks/useAppVersion'
import { listSections } from '../registry/sections'

interface AppSidebarProps {
  activeTabId: string | null
  onSelectTab: (tabId: string) => void
}

export function AppSidebar({ activeTabId, onSelectTab }: AppSidebarProps) {
  const sections = listSections()
  const version = useAppVersion()
  const activeSectionId = activeTabId ? featureRegistry.get(activeTabId)?.sectionId : undefined

  return (
    <Sidebar collapsible="offcanvas" className="border-r border-sidebar-border">
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
        {sections.map((section) => {
          const SectionIcon = section.icon
          const tools = featureRegistry.listBySection(section.id)
          const isActiveSection = section.id === activeSectionId
          return (
            <SidebarGroup key={section.id}>
              <SidebarGroupLabel
                className={cn(
                  'gap-2',
                  isActiveSection && 'text-sidebar-foreground font-medium [&>svg]:text-primary'
                )}
              >
                <SectionIcon aria-hidden strokeWidth={1.75} />
                {section.label}
              </SidebarGroupLabel>
              <SidebarMenuSub>
                {tools.map((tool) => {
                  const ToolIcon = tool.icon
                  const selected = tool.id === activeTabId
                  return (
                    <SidebarMenuSubItem key={tool.id}>
                      <SidebarMenuSubButton
                        asChild
                        isActive={selected}
                        aria-current={selected ? 'page' : undefined}
                      >
                        <button type="button" onClick={() => onSelectTab(tool.id)}>
                          <ToolIcon aria-hidden strokeWidth={1.75} />
                          <span>{tool.label}</span>
                        </button>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  )
                })}
              </SidebarMenuSub>
            </SidebarGroup>
          )
        })}
      </SidebarContent>
      <SidebarFooter className="mt-auto border-t border-sidebar-border px-4 py-3">
        <p className="text-xs text-muted-foreground tabular-nums" title="Versión del software">
          {version ? `v${version}` : '…'}
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}
