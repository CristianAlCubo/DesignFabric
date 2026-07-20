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
      <TabsList
        variant="line"
        className="h-auto w-fit justify-start gap-1 rounded-none bg-transparent p-0"
      >
        {orderedTabs.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            id={`tab-${tab.id}`}
            className="flex-none rounded-none px-3 py-2.5 text-muted-foreground data-active:bg-transparent data-active:font-semibold data-active:text-foreground data-active:shadow-none dark:data-active:bg-transparent after:bg-primary group-data-[variant=line]/tabs-list:data-active:after:opacity-100"
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
