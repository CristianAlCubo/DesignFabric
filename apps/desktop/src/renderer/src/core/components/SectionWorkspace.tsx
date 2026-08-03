import { featureRegistry } from '../registry/featureRegistry'

interface SectionWorkspaceProps {
  activeTabId: string | null
}

export function SectionWorkspace({ activeTabId }: SectionWorkspaceProps) {
  const activeTab = activeTabId ? featureRegistry.get(activeTabId) : undefined
  const ActivePanel = activeTab?.Panel
  const Icon = activeTab?.icon

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {activeTab ? (
        <div className="flex items-center gap-2 border-b border-border px-6 py-3">
          {Icon ? <Icon aria-hidden strokeWidth={1.75} className="size-4 text-muted-foreground" /> : null}
          <h1 className="text-sm font-medium text-foreground">{activeTab.label}</h1>
        </div>
      ) : null}
      <main className="page">{ActivePanel ? <ActivePanel /> : null}</main>
    </div>
  )
}
