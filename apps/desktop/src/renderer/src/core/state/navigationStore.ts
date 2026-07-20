/**
 * Store compartido de navegación en dos niveles (sección sidebar + tab).
 * Vive en `core/` porque es infraestructura transversal: permite que una
 * feature cambie a otra tab de forma programática (ej. "Enviar a escalado")
 * sin que `App.tsx` exponga estado local.
 */
import { create } from 'zustand'

import { featureRegistry } from '../registry/featureRegistry'
import { listSections } from '../registry/sections'
import type { SectionId } from '../registry/types'

interface NavigationState {
  activeSectionId: SectionId | null
  activeTabId: string | null
  lastTabBySection: Partial<Record<SectionId, string>>
  setActiveSection: (sectionId: SectionId) => void
  setActiveTab: (tabId: string) => void
  ensureDefaults: () => void
}

function resolveTabForSection(
  sectionId: SectionId,
  lastTabBySection: Partial<Record<SectionId, string>>
): string | null {
  const tabs = featureRegistry.listBySection(sectionId)
  if (tabs.length === 0) return null

  const remembered = lastTabBySection[sectionId]
  if (remembered && tabs.some((tab) => tab.id === remembered)) {
    return remembered
  }
  return tabs[0].id
}

export const useNavigationStore = create<NavigationState>((set, get) => ({
  activeSectionId: null,
  activeTabId: null,
  lastTabBySection: {},

  setActiveSection: (sectionId) => {
    const tabId = resolveTabForSection(sectionId, get().lastTabBySection)
    set((state) => ({
      activeSectionId: sectionId,
      activeTabId: tabId,
      lastTabBySection: tabId
        ? { ...state.lastTabBySection, [sectionId]: tabId }
        : state.lastTabBySection
    }))
  },

  setActiveTab: (tabId) => {
    const tab = featureRegistry.get(tabId)
    if (!tab) return

    set((state) => ({
      activeSectionId: tab.sectionId,
      activeTabId: tabId,
      lastTabBySection: { ...state.lastTabBySection, [tab.sectionId]: tabId }
    }))
  },

  ensureDefaults: () => {
    const { activeSectionId, activeTabId } = get()
    if (activeSectionId !== null && activeTabId !== null) return

    const firstSection = listSections()[0]
    if (!firstSection) return

    const tabId = resolveTabForSection(firstSection.id, get().lastTabBySection)
    set({
      activeSectionId: firstSection.id,
      activeTabId: tabId,
      lastTabBySection: tabId ? { [firstSection.id]: tabId } : {}
    })
  }
}))
