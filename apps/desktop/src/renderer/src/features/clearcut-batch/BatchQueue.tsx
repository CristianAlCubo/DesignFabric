import { CircleCheckBig, CircleX, FolderOpen, SkipForward } from 'lucide-react'

import { Button } from '@/components/ui/button'

import type { BatchItemResult, BatchReport } from './store'

interface BatchQueueProps {
  items: BatchItemResult[]
  report: BatchReport | null
  outputDir: string | null
  onOpenOutput: () => void
}

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

function StatusIcon({ status }: { status: BatchItemResult['status'] }) {
  if (status === 'succeeded') {
    return <CircleCheckBig size={15} className="batch-queue__icon batch-queue__icon--ok" aria-hidden />
  }
  if (status === 'skipped') {
    return <SkipForward size={15} className="batch-queue__icon batch-queue__icon--skip" aria-hidden />
  }
  return <CircleX size={15} className="batch-queue__icon batch-queue__icon--fail" aria-hidden />
}

export function BatchQueue({ items, report, outputDir, onOpenOutput }: BatchQueueProps) {
  if (items.length === 0 && !report) {
    return (
      <div className="batch-queue batch-queue--empty">
        <p className="muted">La cola del lote se llenará conforme avance el procesamiento.</p>
      </div>
    )
  }

  return (
    <section className="batch-queue">
      {report ? (
        <div className="batch-chips" aria-label="Resumen del lote">
          <span className="batch-chip">
            Total <strong>{report.total}</strong>
          </span>
          <span className="batch-chip batch-chip--ok">
            Éxitos <strong>{report.succeeded}</strong>
          </span>
          <span className="batch-chip batch-chip--fail">
            Fallos <strong>{report.failed}</strong>
          </span>
          <span className="batch-chip batch-chip--skip">
            Omitidos <strong>{report.skipped}</strong>
          </span>
          {report.cancelled ? <span className="batch-chip batch-chip--warn">Cancelado</span> : null}
        </div>
      ) : null}

      <ul className="batch-queue__list">
        {items.map((item) => (
          <li key={`${item.status}:${item.input}`} className="batch-queue__row">
            <StatusIcon status={item.status} />
            <div className="batch-queue__body">
              <span className="batch-queue__name" title={item.input}>
                {basename(item.input)}
              </span>
              {item.error ? <span className="batch-queue__error">{item.error}</span> : null}
              {item.warning ? <span className="batch-queue__warning">{item.warning}</span> : null}
            </div>
          </li>
        ))}
      </ul>

      {outputDir && report ? (
        <Button type="button" variant="outline" onClick={onOpenOutput}>
          <FolderOpen data-icon="inline-start" aria-hidden />
          Abrir carpeta de salida
        </Button>
      ) : null}
    </section>
  )
}
