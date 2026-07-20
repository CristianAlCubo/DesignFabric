/**
 * Store MÍNIMO y compartido para la tab activa del tabpane. Vive en `core/`
 * (no en una feature) porque es infraestructura de navegación transversal:
 * permite que una feature cambie a otra tab de forma programática (ej. el
 * botón "Enviar a escalado" del resultado de eliminación de fondo), sin que
 * `App.tsx` tenga que exponer su estado local para eso.
 */
import { create } from 'zustand'

interface NavigationState {
  activeTabId: string | null
  setActiveTab: (id: string) => void
}

export const useNavigationStore = create<NavigationState>((set) => ({
  activeTabId: null,
  setActiveTab: (id) => set({ activeTabId: id })
}))
