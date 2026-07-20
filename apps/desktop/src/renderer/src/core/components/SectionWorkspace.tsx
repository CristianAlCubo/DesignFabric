import { featureRegistry } from '../registry/featureRegistry'
import { getSection } from '../registry/sections'
import type { SectionId } from '../registry/types'
import { TabPane } from './TabPane'

interface SectionWorkspaceProps {
  sectionId: SectionId | null
  activeTabId: string | null
  onTabChange: (tabId: string) => void
}

export function SectionWorkspace({
  sectionId,
  activeTabId,
  onTabChange
}: SectionWorkspaceProps) {
  const section = sectionId ? getSection(sectionId) : undefined
  const tabs = sectionId ? featureRegistry.listBySection(sectionId) : []
  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]
  const ActivePanel = activeTab?.Panel

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {section ? (
        <header className="px-6 pt-3.5 pb-1">
          <h2 className="text-lg font-semibold tracking-tight text-foreground text-balance">
            {section.label}
          </h2>
        </header>
      ) : null}
      {tabs.length > 0 ? (
        <div className="border-b border-border px-6">
          <TabPane
            tabs={tabs}
            activeId={activeTab?.id ?? ''}
            onChange={onTabChange}
            ariaLabel={
              section
                ? `Subfunciones de ${section.label}`
                : 'Subfunciones'
            }
          />
        </div>
      ) : null}
      <main className="page">{ActivePanel ? <ActivePanel /> : null}</main>
    </div>
  )
}
