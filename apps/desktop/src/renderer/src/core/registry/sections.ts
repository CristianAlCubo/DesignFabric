import { Images, Layers, Sparkles, Wrench } from 'lucide-react'

import type { SectionDescriptor } from './types'

/**
 * Secciones del sidebar (IA de producto fija). Las features se enchufan
 * a estos IDs vía `TabDescriptor.sectionId`.
 */
export const SECTIONS: readonly SectionDescriptor[] = [
  { id: 'generation', label: 'Generación', order: 0, icon: Sparkles },
  { id: 'retouch', label: 'Retocado', order: 1, icon: Layers },
  { id: 'batches', label: 'Lotes', order: 2, icon: Images },
  { id: 'utilities', label: 'Utilidades', order: 3, icon: Wrench }
]

export function listSections(): SectionDescriptor[] {
  return [...SECTIONS].sort((a, b) => a.order - b.order)
}

export function getSection(id: SectionDescriptor['id']): SectionDescriptor | undefined {
  return SECTIONS.find((section) => section.id === id)
}
