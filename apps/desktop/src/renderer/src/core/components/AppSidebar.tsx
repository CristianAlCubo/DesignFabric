import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem
} from '@/components/ui/sidebar'

import { listSections } from '../registry/sections'
import type { SectionId } from '../registry/types'

interface AppSidebarProps {
  activeSectionId: SectionId | null
  onSelect: (sectionId: SectionId) => void
}

export function AppSidebar({ activeSectionId, onSelect }: AppSidebarProps) {
  const sections = listSections()

  return (
    <Sidebar collapsible="none" className="border-r border-sidebar-border">
      <SidebarHeader className="px-4 py-3">
        <span className="text-base font-bold tracking-wide text-sidebar-foreground">
          DesignFabric
        </span>
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
    </Sidebar>
  )
}
