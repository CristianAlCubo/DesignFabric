import type { LucideIcon } from 'lucide-react'
import type { ComponentType } from 'react'

export type SectionId = 'generation' | 'retouch' | 'batches'

export interface SectionDescriptor {
  id: SectionId
  label: string
  order: number
  icon: LucideIcon
}

/** Describe un tab del tabpane unificado; cada feature registra el suyo. */
export interface TabDescriptor {
  id: string
  label: string
  order: number
  sectionId: SectionId
  Panel: ComponentType
}
