import { BrowserWindow } from 'electron'

import type { LogEntry } from '@shared/logEntry'

const MAX_LOG_ENTRIES = 2000

const history: LogEntry[] = []

/** Agrega una entrada al ring buffer (con timestamp autogenerado) y la reenvía a todas las ventanas abiertas. */
export function pushLog(entry: Omit<LogEntry, 'timestamp'>): void {
  const full: LogEntry = { ...entry, timestamp: new Date().toISOString() }

  history.push(full)
  if (history.length > MAX_LOG_ENTRIES) {
    history.splice(0, history.length - MAX_LOG_ENTRIES)
  }

  for (const window of BrowserWindow.getAllWindows()) {
    if (!window.isDestroyed()) {
      window.webContents.send('app-log', full)
    }
  }
}

/** Devuelve una copia del historial de logs acumulado hasta ahora. */
export function getLogHistory(): LogEntry[] {
  return [...history]
}
