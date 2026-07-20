import type { ComponentType } from 'react'

/** Describe un tab del tabpane unificado; cada feature registra el suyo. */
export interface TabDescriptor {
  id: string
  label: string
  order: number
  Panel: ComponentType
}
