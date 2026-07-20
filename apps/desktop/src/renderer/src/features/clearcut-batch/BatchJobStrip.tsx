import { CircleDashed, LoaderCircle, Play, Square } from 'lucide-react'

import type { BatchJobPhase } from './store'

export interface BatchProgressDisplay {
  current: number
  total: number
  path: string
}

interface BatchJobStripProps {
  phase: BatchJobPhase
  progress: BatchProgressDisplay | null
  startedAt: number | null
  itemCompletedAt: number[]
  canRun: boolean
  isRunning: boolean
  now: number
  onRun: () => void
  onCancel: () => void
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function estimateRemainingMs(
  startedAt: number | null,
  itemCompletedAt: number[],
  progress: BatchProgressDisplay | null,
  now: number
): number | null {
  if (!progress || progress.total <= 0 || itemCompletedAt.length === 0 || startedAt === null) {
    return null
  }
  void now
  const elapsed = itemCompletedAt[itemCompletedAt.length - 1] - startedAt
  const avg = elapsed / itemCompletedAt.length
  const remainingItems = Math.max(0, progress.total - itemCompletedAt.length)
  return avg * remainingItems
}

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

export function BatchJobStrip({
  phase,
  progress,
  startedAt,
  itemCompletedAt,
  canRun,
  isRunning,
  now,
  onRun,
  onCancel
}: BatchJobStripProps) {
  const current = progress?.current ?? itemCompletedAt.length
  const total = progress?.total ?? 0
  const ratio = total > 0 ? Math.min(1, current / total) : isRunning ? 0.05 : 0
  const elapsedMs = startedAt !== null ? now - startedAt : 0
  const etaMs = estimateRemainingMs(startedAt, itemCompletedAt, progress, now)
  const currentName = progress?.path ? basename(progress.path) : null

  const statusLabel =
    phase === 'running'
      ? 'Procesando'
      : phase === 'cancelled'
        ? 'Cancelado'
        : phase === 'done'
          ? 'Completado'
          : phase === 'error'
            ? 'Error'
            : 'En espera'

  return (
    <section className="batch-job-strip" aria-live="polite">
      <div className="batch-job-strip__head">
        <div className="batch-job-strip__title-row">
          {isRunning ? (
            <LoaderCircle className="batch-job-strip__spinner" size={16} aria-hidden />
          ) : (
            <CircleDashed size={16} aria-hidden />
          )}
          <h2 className="batch-job-strip__title">{statusLabel}</h2>
        </div>
        <div className="batch-job-strip__metrics">
          <span className="batch-job-strip__metric">
            <span className="batch-job-strip__metric-label">Avance</span>
            <span className="batch-job-strip__metric-value">
              {total > 0 ? `${current} / ${total}` : '—'}
            </span>
          </span>
          <span className="batch-job-strip__metric">
            <span className="batch-job-strip__metric-label">Transcurrido</span>
            <span className="batch-job-strip__metric-value">
              {startedAt !== null ? formatDuration(elapsedMs) : '—'}
            </span>
          </span>
          <span className="batch-job-strip__metric">
            <span className="batch-job-strip__metric-label">ETA</span>
            <span className="batch-job-strip__metric-value">
              {etaMs !== null ? formatDuration(etaMs) : '—'}
            </span>
          </span>
        </div>
      </div>

      <div
        className="batch-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total || 100}
        aria-valuenow={current}
        aria-label="Progreso del lote"
      >
        <div className="batch-progress__fill" style={{ transform: `scaleX(${ratio})` }} />
      </div>

      <p className="batch-job-strip__file">
        {currentName
          ? `Archivo actual: ${currentName}`
          : isRunning
            ? 'Preparando lote…'
            : 'El progreso del lote aparecerá aquí.'}
      </p>

      <div className="batch-job-strip__actions">
        {isRunning ? (
          <button type="button" className="btn btn--danger" onClick={onCancel}>
            <Square size={14} aria-hidden />
            Cancelar
          </button>
        ) : (
          <button
            type="button"
            className="btn btn--primary batch-job-strip__run"
            onClick={onRun}
            disabled={!canRun}
          >
            <Play size={14} aria-hidden />
            Procesar lote
          </button>
        )}
      </div>
    </section>
  )
}
