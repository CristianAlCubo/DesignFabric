import type { TabDescriptor } from './types'

/**
 * Registro central de features (patrón Registry): cada feature se registra
 * a sí misma al ser importada (ver `features/index.ts`), sin que `App.tsx`
 * necesite conocer la lista de features de antemano.
 */
class FeatureRegistry {
  private tabs = new Map<string, TabDescriptor>()

  register(tab: TabDescriptor): void {
    this.tabs.set(tab.id, tab)
  }

  list(): TabDescriptor[] {
    return [...this.tabs.values()].sort((a, b) => a.order - b.order)
  }
}

export const featureRegistry = new FeatureRegistry()
