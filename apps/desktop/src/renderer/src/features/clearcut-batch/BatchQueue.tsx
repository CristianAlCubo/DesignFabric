import { useEffect, useMemo, useState } from 'react'
import { CircleCheckBig, CircleX, FolderOpen, SkipForward } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import type { ProgressEvent } from '../../core/api/types'
import type { BatchItemResult, BatchReport } from './store'
import { VirtualList } from './VirtualList'

type QueueFilter = 'all' | 'failed' | 'succeeded' | 'skipped'

interface BatchQueueProps {
  items: BatchItemResult[]
  report: BatchReport | null
  outputDir: string | null
  isRunning: boolean
  progressEvents: ProgressEvent[]
  onOpenOutput: () => void
}

const ROW_HEIGHT = 52
const RECENT_LIMIT = 40

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

function StatusIcon({ status }: { status: BatchItemResult['status'] }) {
  if (status === 'succeeded') {
    return <CircleCheckBig className="batch-queue__icon batch-queue__icon--ok" aria-hidden />
  }
  if (status === 'skipped') {
    return <SkipForward className="batch-queue__icon batch-queue__icon--skip" aria-hidden />
  }
  return <CircleX className="batch-queue__icon batch-queue__icon--fail" aria-hidden />
}

export function BatchQueue({
  items,
  report,
  outputDir,
  isRunning,
  progressEvents,
  onOpenOutput
}: BatchQueueProps) {
  const [filter, setFilter] = useState<QueueFilter>('all')
  const [query, setQuery] = useState('')

  useEffect(() => {
    if (!report) {
      setFilter('all')
      setQuery('')
      return
    }
    setFilter(report.failed > 0 ? 'failed' : 'all')
    setQuery('')
  }, [report])

  const recentActivity = useMemo(() => {
    const seen = new Set<string>()
    const paths: string[] = []
    for (let index = progressEvents.length - 1; index >= 0; index -= 1) {
      const event = progressEvents[index]
      if (event.type !== 'progress' || !event.detail) continue
      if (seen.has(event.detail)) continue
      seen.add(event.detail)
      paths.push(event.detail)
      if (paths.length >= RECENT_LIMIT) break
    }
    return paths
  }, [progressEvents])

  const filteredItems = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    let next = items
    if (filter !== 'all') {
      next = next.filter((item) => item.status === filter)
    }
    if (normalized) {
      next = next.filter((item) => basename(item.input).toLowerCase().includes(normalized))
    }
    if (filter === 'all') {
      next = [...next].sort((a, b) => {
        const rank = (status: BatchItemResult['status']): number =>
          status === 'failed' ? 0 : status === 'skipped' ? 1 : 2
        return rank(a.status) - rank(b.status)
      })
    }
    return next
  }, [items, filter, query])

  if (items.length === 0 && !report) {
    return (
      <div className="batch-queue batch-queue--empty">
        {isRunning ? (
          <div className="flex min-h-0 flex-1 flex-col gap-3">
            <p className="muted">
              Procesando lote. El detalle completo (éxitos, fallos y avisos) aparece al terminar.
            </p>
            {recentActivity.length > 0 ? (
              <>
                <p className="batch-queue__section-label">Actividad reciente</p>
                <ul className="batch-queue__recent">
                  {recentActivity.map((path, index) => (
                    <li key={`${path}:${index}`} className="batch-queue__row batch-queue__row--compact">
                      <CircleCheckBig
                        className="batch-queue__icon batch-queue__icon--ok"
                        aria-hidden
                      />
                      <span className="batch-queue__name" title={path}>
                        {basename(path)}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="muted">Esperando el primer archivo…</p>
            )}
          </div>
        ) : (
          <p className="muted">
            Configura la entrada y pulsa Procesar. Aquí verás el resultado del lote y podrás filtrar
            fallos.
          </p>
        )}
      </div>
    )
  }

  return (
    <section className="batch-queue">
      {report ? (
        <div className="batch-chips" aria-label="Resumen del lote">
          <button
            type="button"
            className={`batch-chip${filter === 'all' ? ' batch-chip--active' : ''}`}
            onClick={() => setFilter('all')}
          >
            Total <strong>{report.total}</strong>
          </button>
          <button
            type="button"
            className={`batch-chip batch-chip--ok${filter === 'succeeded' ? ' batch-chip--active' : ''}`}
            onClick={() => setFilter('succeeded')}
          >
            Éxitos <strong>{report.succeeded}</strong>
          </button>
          <button
            type="button"
            className={`batch-chip batch-chip--fail${filter === 'failed' ? ' batch-chip--active' : ''}`}
            onClick={() => setFilter('failed')}
          >
            Fallos <strong>{report.failed}</strong>
          </button>
          <button
            type="button"
            className={`batch-chip batch-chip--skip${filter === 'skipped' ? ' batch-chip--active' : ''}`}
            onClick={() => setFilter('skipped')}
          >
            Omitidos <strong>{report.skipped}</strong>
          </button>
          {report.cancelled ? (
            <Badge variant="outline" className="text-warning">
              Cancelado
            </Badge>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          size="sm"
          value={filter}
          onValueChange={(value) => {
            if (
              value === 'all' ||
              value === 'failed' ||
              value === 'succeeded' ||
              value === 'skipped'
            ) {
              setFilter(value)
            }
          }}
          aria-label="Filtrar resultados"
          className="w-full sm:w-auto"
        >
          <ToggleGroupItem value="all" className="flex-1 sm:flex-none">
            Todos
          </ToggleGroupItem>
          <ToggleGroupItem value="failed" className="flex-1 sm:flex-none">
            Fallos
          </ToggleGroupItem>
          <ToggleGroupItem value="skipped" className="flex-1 sm:flex-none">
            Omitidos
          </ToggleGroupItem>
          <ToggleGroupItem value="succeeded" className="flex-1 sm:flex-none">
            Éxitos
          </ToggleGroupItem>
        </ToggleGroup>
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar por nombre…"
          aria-label="Buscar en resultados"
          className="sm:max-w-56"
        />
      </div>

      {filteredItems.length === 0 ? (
        <p className="muted">Ningún ítem coincide con el filtro.</p>
      ) : (
        <VirtualList
          items={filteredItems}
          rowHeight={ROW_HEIGHT}
          getKey={(item, index) => `${item.input}:${item.status}:${index}`}
          renderRow={(item) => (
            <div className="batch-queue__row batch-queue__row--virtual">
              <StatusIcon status={item.status} />
              <div className="batch-queue__body">
                <span className="batch-queue__name" title={item.input}>
                  {basename(item.input)}
                </span>
                {item.error ? <span className="batch-queue__error">{item.error}</span> : null}
                {item.warning ? <span className="batch-queue__warning">{item.warning}</span> : null}
              </div>
            </div>
          )}
        />
      )}

      <p className="batch-queue__count muted tabular-nums">
        Mostrando {filteredItems.length} de {items.length}
      </p>

      {outputDir && report ? (
        <AppButton type="button" variant="outline" icon={FolderOpen} onClick={onOpenOutput}>
          Abrir carpeta de salida
        </AppButton>
      ) : null}
    </section>
  )
}
