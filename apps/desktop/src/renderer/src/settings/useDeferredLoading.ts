import { useEffect, useState } from 'react'

/**
 * Delayed loading indicator: evita el flash skeleton→contenido cuando la
 * carga termina rápido (IPC/local). Solo muestra loading si `pending` dura
 * más que `delayMs` (patrón "threshold / deferred loading UI").
 */
export function useDeferredLoading(pending: boolean, delayMs = 200): boolean {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!pending) {
      setShow(false)
      return
    }
    const timer = window.setTimeout(() => setShow(true), delayMs)
    return () => window.clearTimeout(timer)
  }, [pending, delayMs])

  return show
}
