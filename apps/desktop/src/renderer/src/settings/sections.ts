import { Brain, Image as ImageIcon, Info, KeyRound, type LucideIcon } from 'lucide-react'

export type SettingsSectionId = 'general' | 'openrouter' | 'language-models' | 'image-models'

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
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    description: 'API key de la cuenta OpenRouter (texto e imagen).',
    icon: KeyRound
  },
  {
    id: 'language-models',
    label: 'Modelos de lenguaje',
    description: 'Configura el modelo de cada provider de texto.',
    icon: Brain
  },
  {
    id: 'image-models',
    label: 'Modelos de imagen',
    description: 'Configura el modelo de cada provider de imagen.',
    icon: ImageIcon
  }
] as const

export function getSettingsSection(id: SettingsSectionId): SettingsSection {
  const section = SETTINGS_SECTIONS.find((item) => item.id === id)
  if (!section) throw new Error(`Sección de configuración desconocida: ${id}`)
  return section
}
