import type { SectionId, TabDescriptor } from './types'

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

  get(id: string): TabDescriptor | undefined {
    return this.tabs.get(id)
  }

  list(): TabDescriptor[] {
    return [...this.tabs.values()].sort((a, b) => a.order - b.order)
  }

  listBySection(sectionId: SectionId): TabDescriptor[] {
    return this.list().filter((tab) => tab.sectionId === sectionId)
  }
}

export const featureRegistry = new FeatureRegistry()
