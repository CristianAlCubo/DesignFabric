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
    <div className="section-workspace">
      {section ? (
        <header className="section-workspace__header">
          <h2 className="section-workspace__title">{section.label}</h2>
        </header>
      ) : null}
      {tabs.length > 0 ? (
        <div className="section-workspace__tabs">
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
