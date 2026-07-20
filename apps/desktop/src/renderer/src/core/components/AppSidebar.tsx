import { listSections } from '../registry/sections'
import type { SectionId } from '../registry/types'

interface AppSidebarProps {
  activeSectionId: SectionId | null
  onSelect: (sectionId: SectionId) => void
}

export function AppSidebar({ activeSectionId, onSelect }: AppSidebarProps) {
  const sections = listSections()

  return (
    <nav className="app-sidebar" aria-label="Menú principal">
      <div className="app-sidebar__brand">DesignFabric</div>
      <ul className="app-sidebar__list">
        {sections.map((section) => {
          const selected = section.id === activeSectionId
          const Icon = section.icon
          return (
            <li key={section.id}>
              <button
                type="button"
                className={
                  selected
                    ? 'app-sidebar__item app-sidebar__item--active'
                    : 'app-sidebar__item'
                }
                aria-current={selected ? 'page' : undefined}
                onClick={() => onSelect(section.id)}
              >
                <Icon className="app-sidebar__icon" aria-hidden size={22} strokeWidth={1.75} />
                <span className="app-sidebar__label">{section.label}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
