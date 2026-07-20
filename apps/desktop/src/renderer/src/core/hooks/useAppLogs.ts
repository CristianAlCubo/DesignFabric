/**
 * Suscripción a la consola de observabilidad: trae el historial acumulado
 * en el proceso main y luego recibe nuevas líneas en vivo (backend +
 * proceso main de Electron). Acotado a un máximo de líneas en memoria para
 * no crecer sin límite en sesiones largas.
 */

import { useEffect, useState } from 'react'
import type { LogEntry } from '@shared/logEntry'

const MAX_ENTRIES = 2000

export function useAppLogs(): LogEntry[] {
  const [entries, setEntries] = useState<LogEntry[]>([])

  useEffect(() => {
    let cancelled = false

    window.designfabric.getLogHistory().then((history) => {
      if (!cancelled) setEntries(history)
    })

    const unsubscribe = window.designfabric.onLog((entry) => {
      setEntries((previous) => {
        const next = [...previous, entry]
        return next.length > MAX_ENTRIES ? next.slice(next.length - MAX_ENTRIES) : next
      })
    })

    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [])

  return entries
}
