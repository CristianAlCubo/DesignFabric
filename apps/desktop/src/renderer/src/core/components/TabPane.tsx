import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

import type { TabDescriptor } from '../registry/types'

interface TabPaneProps {
  tabs: TabDescriptor[]
  activeId: string
  onChange: (id: string) => void
  ariaLabel?: string
}

export function TabPane({
  tabs,
  activeId,
  onChange,
  ariaLabel = 'Subfunciones'
}: TabPaneProps) {
  const orderedTabs = [...tabs].sort((a, b) => a.order - b.order)

  return (
    <Tabs
      value={activeId}
      onValueChange={onChange}
      className="w-full"
      aria-label={ariaLabel}
    >
      <TabsList variant="line" className="h-auto w-full justify-start rounded-none p-0">
        {orderedTabs.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            id={`tab-${tab.id}`}
            className="rounded-none px-4 py-2.5"
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
