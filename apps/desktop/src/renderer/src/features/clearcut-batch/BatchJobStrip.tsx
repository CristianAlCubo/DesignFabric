import { CircleDashed, LoaderCircle, Play, Square } from 'lucide-react'

import { Badge } from '@/components/ui/badge'

import { AppButton } from '../../core/components/AppButton'
import { estimateBatchRemainingMs } from './batchProgress'
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
  lastCompletedAt: number | null
  canRun: boolean
  runBlockers: string[]
  isRunning: boolean
  inputCount: number | null
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

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

export function BatchJobStrip({
  phase,
  progress,
  startedAt,
  lastCompletedAt,
  canRun,
  runBlockers,
  isRunning,
  inputCount,
  now,
  onRun,
  onCancel
}: BatchJobStripProps) {
  const completed = progress?.current ?? 0
  const total = progress?.total ?? 0
  const ratio = total > 0 ? Math.min(1, completed / total) : isRunning ? 0.05 : 0
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0
  const elapsedMs = startedAt !== null ? now - startedAt : 0
  const etaMs = estimateBatchRemainingMs(startedAt, progress, now, lastCompletedAt)
  const currentName = progress?.path ? basename(progress.path) : null
  const allDone = total > 0 && completed >= total

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

  const runLabel =
    inputCount !== null && inputCount > 0
      ? `Procesar ${inputCount} imagen${inputCount === 1 ? '' : 'es'}`
      : 'Procesar lote'

  const fileLine = currentName
    ? allDone || !isRunning
      ? `Último archivo: ${currentName}`
      : `Archivo actual: ${currentName}`
    : isRunning
      ? 'Preparando lote…'
      : 'El progreso del lote aparecerá aquí.'

  return (
    <section className="batch-job-strip" aria-live="polite">
      <div className="batch-job-strip__head">
        <div className="batch-job-strip__title-row">
          {isRunning ? (
            <LoaderCircle className="batch-job-strip__spinner" size={16} aria-hidden />
          ) : (
            <CircleDashed size={16} aria-hidden />
          )}
          <Badge variant={phase === 'error' ? 'destructive' : 'secondary'}>{statusLabel}</Badge>
        </div>
        <div className="batch-job-strip__hero" aria-label="Avance del lote">
          <span className="batch-job-strip__hero-value tabular-nums">
            {total > 0 ? `${completed} / ${total}` : '—'}
          </span>
          <span className="batch-job-strip__hero-meta tabular-nums">
            {total > 0 ? `${percent}% completado` : 'Sin lote activo'}
          </span>
        </div>
      </div>

      <div
        className="batch-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total || 100}
        aria-valuenow={completed}
        aria-label="Progreso del lote"
      >
        <div className="batch-progress__fill" style={{ transform: `scaleX(${ratio})` }} />
      </div>

      <div className="batch-job-strip__meta-row">
        <span className="batch-job-strip__metric">
          <span className="batch-job-strip__metric-label">Transcurrido</span>
          <span className="batch-job-strip__metric-value tabular-nums">
            {startedAt !== null ? formatDuration(elapsedMs) : '—'}
          </span>
        </span>
        <span className="batch-job-strip__metric">
          <span className="batch-job-strip__metric-label">ETA</span>
          <span className="batch-job-strip__metric-value tabular-nums">
            {etaMs !== null ? formatDuration(etaMs) : '—'}
          </span>
        </span>
      </div>

      <p className="batch-job-strip__file">{fileLine}</p>

      <div className="batch-job-strip__actions">
        {isRunning ? (
          <AppButton type="button" variant="destructive" icon={Square} onClick={onCancel}>
            Cancelar
          </AppButton>
        ) : (
          <div className="flex w-full flex-col gap-2">
            <AppButton
              type="button"
              className="batch-job-strip__run"
              icon={Play}
              onClick={onRun}
              disabled={!canRun}
            >
              {runLabel}
            </AppButton>
            {!canRun && runBlockers.length > 0 ? (
              <ul className="batch-job-strip__blockers" aria-label="Requisitos pendientes">
                {runBlockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            ) : null}
          </div>
        )}
      </div>
    </section>
  )
}
