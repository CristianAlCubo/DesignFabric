/**
 * Deriva un snapshot estable de progreso a partir del historial WS.
 * No depende del último evento (warnings/completed sin current/total no
 * borran el avance).
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import type { ProgressEvent } from '../../core/api/types'
import type { BatchProgressDisplay } from './BatchJobStrip'

export function useStickyBatchProgress(events: ProgressEvent[]): BatchProgressDisplay | null {
  return useMemo(() => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index]
      if (event.total === null) continue
      if (event.type !== 'progress' && event.type !== 'started') continue

      return {
        current: event.current ?? 0,
        total: event.total,
        path: event.detail ?? event.message ?? ''
      }
    }
    return null
  }, [events])
}

/** Marca de tiempo del último cambio de `progress.current` (ítems completados). */
export function useProgressAnchor(progress: BatchProgressDisplay | null): number | null {
  const [anchorAt, setAnchorAt] = useState<number | null>(null)
  const completedRef = useRef<number | null>(null)

  useEffect(() => {
    if (!progress) {
      completedRef.current = null
      setAnchorAt(null)
      return
    }
    if (completedRef.current !== progress.current) {
      completedRef.current = progress.current
      setAnchorAt(performance.now())
    }
  }, [progress])

  return anchorAt
}

/**
 * ETA con promedio fijado al último ítem completado y cuenta atrás con `now`.
 * `progress.current` = ítems terminados (no el índice “en curso”).
 */
export function estimateBatchRemainingMs(
  startedAt: number | null,
  progress: BatchProgressDisplay | null,
  now: number,
  lastCompletedAt: number | null
): number | null {
  if (!progress || progress.total <= 0 || startedAt === null) return null

  const completed = progress.current
  if (completed <= 0 || lastCompletedAt === null) return null

  const elapsedToLastCompletion = Math.max(0, lastCompletedAt - startedAt)
  const avgPerItem = elapsedToLastCompletion / completed
  const remainingItems = Math.max(0, progress.total - completed)
  const spentOnCurrent = Math.max(0, now - lastCompletedAt)
  return Math.max(0, avgPerItem * remainingItems - spentOnCurrent)
}
