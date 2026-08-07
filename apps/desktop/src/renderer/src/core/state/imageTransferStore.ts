/**
 * Bus de transferencia de imágenes entre pestañas.
 *
 * Generaliza el antiguo `sendToScale` (acoplado al par fijo remove-background →
 * scale): cualquier pantalla puede enviar el resultado de una imagen como entrada
 * de otra pestaña sin importar el store del destino. El origen llama `send(tabId,
 * source)`, que deja una transferencia pendiente y navega; la `ImageInputZone` de
 * la pestaña destino la `consume()` al activarse y precarga su entrada.
 */
import { create } from 'zustand'

import type { ImageSource } from '../imaging/imageSource'
import { useNavigationStore } from './navigationStore'

interface PendingTransfer {
  targetTabId: string
  source: ImageSource
}

interface ImageTransferState {
  pending: PendingTransfer | null
  /** Envía `source` como entrada de `targetTabId` y navega a esa pestaña. */
  send: (targetTabId: string, source: ImageSource) => void
  /** Devuelve y limpia la transferencia pendiente si es para `tabId`; si no, `null`. */
  consume: (tabId: string) => ImageSource | null
}

export const useImageTransferStore = create<ImageTransferState>((set, get) => ({
  pending: null,

  send: (targetTabId, source) => {
    set({ pending: { targetTabId, source } })
    useNavigationStore.getState().setActiveTab(targetTabId)
  },

  consume: (tabId) => {
    const { pending } = get()
    if (!pending || pending.targetTabId !== tabId) return null
    set({ pending: null })
    return pending.source
  }
}))
