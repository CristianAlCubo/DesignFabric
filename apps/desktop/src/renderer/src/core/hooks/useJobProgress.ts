/**
 * Hook de WebSocket: se suscribe al stream de progreso de un job y acumula
 * los eventos recibidos en orden. La conexión se cierra automáticamente al
 * desmontar o al cambiar de `jobId`.
 */

import { useEffect, useRef, useState } from 'react'

import { getBackendBaseUrl } from '../api/httpClient'
import type { ProgressEvent } from '../api/types'

interface JobProgressState {
  events: ProgressEvent[]
  latestEvent: ProgressEvent | null
  isConnected: boolean
}

export function useJobProgress(jobId: string | null): JobProgressState {
  const [events, setEvents] = useState<ProgressEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    setEvents([])
    socketRef.current?.close()
    socketRef.current = null

    if (!jobId) return

    let cancelled = false

    getBackendBaseUrl().then((baseUrl) => {
      if (cancelled) return

      const wsUrl = baseUrl.replace(/^http/, 'ws')
      const socket = new WebSocket(`${wsUrl}/api/jobs/${jobId}/ws`)
      socketRef.current = socket

      socket.onopen = () => setIsConnected(true)
      socket.onclose = () => setIsConnected(false)
      socket.onmessage = (message: MessageEvent<string>) => {
        const event = JSON.parse(message.data) as ProgressEvent
        setEvents((previous) => [...previous, event])
      }
    })

    return () => {
      cancelled = true
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [jobId])

  return { events, latestEvent: events[events.length - 1] ?? null, isConnected }
}
