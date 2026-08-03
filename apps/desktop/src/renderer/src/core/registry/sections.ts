import { Boxes, Layers, Sparkles } from 'lucide-react'

import type { SectionDescriptor } from './types'

/**
 * Secciones del sidebar, agrupadas por etapa del pipeline (crear → retocar →
 * lote/exportar). Las features se enchufan a estos IDs vía
 * `TabDescriptor.sectionId` — no hay lógica de agrupación fuera de este
 * archivo.
 */
export const SECTIONS: readonly SectionDescriptor[] = [
  { id: 'create', label: 'Crear', order: 0, icon: Sparkles },
  { id: 'retouch', label: 'Retocar', order: 1, icon: Layers },
  { id: 'batch-export', label: 'Lote y Exportación', order: 2, icon: Boxes }
]

export function listSections(): SectionDescriptor[] {
  return [...SECTIONS].sort((a, b) => a.order - b.order)
}

export function getSection(id: SectionDescriptor['id']): SectionDescriptor | undefined {
  return SECTIONS.find((section) => section.id === id)
}
