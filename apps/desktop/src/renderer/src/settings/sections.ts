import { Info, type LucideIcon } from 'lucide-react'

export type SettingsSectionId = 'general'

export interface SettingsSection {
  id: SettingsSectionId
  label: string
  description: string
  icon: LucideIcon
}

export const SETTINGS_SECTIONS: readonly SettingsSection[] = [
  {
    id: 'general',
    label: 'General',
    description: 'Preferencias generales de la aplicación.',
    icon: Info
  }
] as const

export function getSettingsSection(id: SettingsSectionId): SettingsSection {
  const section = SETTINGS_SECTIONS.find((item) => item.id === id)
  if (!section) throw new Error(`Sección de configuración desconocida: ${id}`)
  return section
}
