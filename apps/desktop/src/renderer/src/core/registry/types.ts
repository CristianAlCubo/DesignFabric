import type { LucideIcon } from 'lucide-react'
import type { ComponentType } from 'react'

export type SectionId = 'create' | 'retouch' | 'batch-export'

export interface SectionDescriptor {
  id: SectionId
  label: string
  order: number
  icon: LucideIcon
}

/** Describe una herramienta del árbol de navegación; cada feature registra la suya. */
export interface TabDescriptor {
  id: string
  label: string
  order: number
  sectionId: SectionId
  icon: LucideIcon
  Panel: ComponentType
}
