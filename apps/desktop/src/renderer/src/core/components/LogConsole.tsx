/**
 * Consola de observabilidad: muestra en vivo todo lo que loguean el backend
 * (Python/uvicorn) y el proceso main de Electron, con auto-scroll y
 * resaltado por severidad. Se monta en el ConsoleSheet del shell (y en
 * SetupWizard / FeatureNotInstalled durante instalación). El historial se
 * conserva en el proceso main aunque el panel esté oculto.
 */

import { useEffect, useRef, useState } from 'react'
import type { LogEntry } from '@shared/logEntry'

import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

import { useAppLogs } from '../hooks/useAppLogs'

function severityClass(entry: LogEntry): string {
  if (entry.stream === 'stderr' || entry.stream === 'error') return 'log-console__line--error'
  if (/\bWARNING\b/.test(entry.line)) return 'log-console__line--warning'
  return ''
}

export function LogConsole() {
  const entries = useAppLogs()
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [entries, autoScroll])

  return (
    <div className="log-console">
      <div className="log-console__toolbar">
        <span>{entries.length} líneas</span>
        <div className="flex items-center gap-2">
          <Checkbox
            id="log-autoscroll"
            checked={autoScroll}
            onCheckedChange={(checked) => setAutoScroll(checked === true)}
          />
          <Label htmlFor="log-autoscroll" className="font-normal">
            Auto-scroll
          </Label>
        </div>
      </div>
      <div className="log-console__body">
        {entries.map((entry, index) => (
          <div key={index} className={cn('log-console__line', severityClass(entry))}>
            <span className="log-console__timestamp">{entry.timestamp.slice(11, 19)}</span>
            <span className="log-console__source">[{entry.source}]</span>
            <span className="log-console__text">{entry.line}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
