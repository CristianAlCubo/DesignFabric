import type { TabDescriptor } from '../registry/types'

interface TabPaneProps {
  tabs: TabDescriptor[]
  activeId: string
  onChange: (id: string) => void
}

export function TabPane({ tabs, activeId, onChange }: TabPaneProps) {
  const orderedTabs = [...tabs].sort((a, b) => a.order - b.order)

  return (
    <div className="tabpane" role="tablist" aria-label="Funciones de DesignFabric">
      {orderedTabs.map((tab) => {
        const selected = tab.id === activeId
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`panel-${tab.id}`}
            className={selected ? 'tabpane__tab tabpane__tab--active' : 'tabpane__tab'}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
