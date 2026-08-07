/**
 * Hook que unifica la adquisición de la imagen de entrada de una pantalla desde
 * los tres orígenes globales (diálogo nativo, portapapeles y arrastrar-y-soltar),
 * más las transferencias entre pestañas, y gestiona el ciclo de vida del archivo
 * temporal: cada vez que se adquiere una fuente nueva, descarta el temporal de la
 * entrada anterior (`disposeTempImage` es no-op si la ruta previa no era temporal,
 * p. ej. venía del diálogo o de otra pestaña), garantizando ≤1 temporal por input.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

import { useImageTransferStore } from '../state/imageTransferStore'
import { acquireFromDataTransfer, acquireFromDialog, type ImageSource } from './imageSource'

interface UseImageSourceOptions {
  /** Ruta de la entrada actual (para descartar su temporal al reemplazarla). */
  currentPath: string | null
  /** Se invoca con la fuente adquirida (el store la aplica a su estado). */
  onSource: (source: ImageSource) => void | Promise<void>
  onError?: (message: string) => void
  disabled?: boolean
  /** Id de esta pestaña, para consumir transferencias dirigidas a ella. */
  tabId?: string
}

interface UseImageSourceResult {
  openDialog: () => Promise<void>
  handleDrop: (event: React.DragEvent) => void
  handleDragOver: (event: React.DragEvent) => void
  handleDragLeave: (event: React.DragEvent) => void
  isDragOver: boolean
}

/** ¿El foco está en un control de texto? Entonces Ctrl+V es un pegado normal, no de imagen. */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable
}

export function useImageSource({
  currentPath,
  onSource,
  onError,
  disabled = false,
  tabId
}: UseImageSourceOptions): UseImageSourceResult {
  const [isDragOver, setIsDragOver] = useState(false)

  // Refs para que los listeners (paste global) siempre vean el estado más reciente
  // sin recrearse en cada render.
  const currentPathRef = useRef(currentPath)
  currentPathRef.current = currentPath
  const disabledRef = useRef(disabled)
  disabledRef.current = disabled

  const pendingTransfer = useImageTransferStore((state) => state.pending)
  const consumeTransfer = useImageTransferStore((state) => state.consume)

  const apply = useCallback(
    async (source: ImageSource) => {
      const previous = currentPathRef.current
      if (previous) void window.designfabric.disposeTempImage(previous)
      await onSource(source)
    },
    [onSource]
  )

  const openDialog = useCallback(async () => {
    if (disabledRef.current) return
    try {
      const source = await acquireFromDialog()
      if (source) await apply(source)
    } catch (err) {
      onError?.(err instanceof Error ? err.message : 'No se pudo abrir la imagen.')
    }
  }, [apply, onError])

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      setIsDragOver(false)
      if (disabledRef.current) return
      const data = event.dataTransfer
      void (async () => {
        try {
          const source = await acquireFromDataTransfer(data, 'drop')
          if (source) await apply(source)
        } catch (err) {
          onError?.(err instanceof Error ? err.message : 'No se pudo cargar la imagen soltada.')
        }
      })()
    },
    [apply, onError]
  )

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    if (disabledRef.current) return
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    setIsDragOver(false)
  }, [])

  // Pegar con Ctrl+V en cualquier parte de la pantalla (salvo mientras se escribe
  // en un campo de texto). Se dirige siempre a la zona de entrada.
  useEffect(() => {
    function onPaste(event: ClipboardEvent): void {
      if (disabledRef.current || isTypingTarget(event.target)) return
      const data = event.clipboardData
      const hasImage = data && Array.from(data.files).some((f) => f.type.startsWith('image/'))
      if (!hasImage) return
      event.preventDefault()
      void (async () => {
        try {
          const source = await acquireFromDataTransfer(data, 'clipboard')
          if (source) await apply(source)
        } catch (err) {
          onError?.(err instanceof Error ? err.message : 'No se pudo pegar la imagen.')
        }
      })()
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [apply, onError])

  // Consumir una transferencia dirigida a esta pestaña (ej. "Enviar a escalado").
  useEffect(() => {
    if (!tabId || !pendingTransfer || pendingTransfer.targetTabId !== tabId) return
    const source = consumeTransfer(tabId)
    if (source) void apply(source)
  }, [tabId, pendingTransfer, consumeTransfer, apply])

  return { openDialog, handleDrop, handleDragOver, handleDragLeave, isDragOver }
}
