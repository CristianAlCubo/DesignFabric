/**
 * Panel de progreso de un job: agrupa los eventos WebSocket por fase
 * (generación de prompts / generación de imágenes), replicando visualmente
 * las barras `rich` que muestra el CLI. Genérico: reutilizado por las
 * features `designfabric-batch` y `designfabric-single`.
 */

import { Images, MessageSquareText, Square } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { AppButton } from './AppButton'
import { useJobProgress } from '../hooks/useJobProgress'
import { ProgressBar } from './ProgressBar'

interface JobProgressPanelProps {
  jobId: string | null
  /** Si true, muestra el botón Cancelar. */
  cancellable?: boolean
  cancelling?: boolean
  onCancel?: () => void
}

const PHASE_META: Record<string, { label: string; icon: LucideIcon }> = {
  prompt_generation: { label: 'Generación de prompts', icon: MessageSquareText },
  image_generation: { label: 'Generación de imágenes', icon: Images }
}

export function JobProgressPanel({
  jobId,
  cancellable = false,
  cancelling = false,
  onCancel
}: JobProgressPanelProps) {
  const { events } = useJobProgress(jobId)

  if (!jobId || (events.length === 0 && !cancellable)) return null

  const phases = Array.from(new Set(events.map((event) => event.phase)))

  return (
    <div className="flex flex-col gap-3 border-t border-border bg-card px-4 py-3">
      {phases.map((phase) => {
        const phaseEvents = events.filter((event) => event.phase === phase)
        const lastProgressOrStart = [...phaseEvents].reverse().find((e) => e.total !== null) ?? phaseEvents[0]
        const warnings = phaseEvents.filter((event) => event.type === 'warning')
        const meta = PHASE_META[phase]
        const Icon = meta?.icon
        const labelBase = meta?.label ?? phase

        return (
          <div key={phase} className="flex flex-col gap-1.5">
            <ProgressBar
              current={lastProgressOrStart.current ?? 0}
              total={lastProgressOrStart.total ?? 0}
              label={
                <span className="inline-flex items-center gap-1.5">
                  {Icon ? <Icon className="size-3.5 shrink-0" aria-hidden /> : null}
                  <span>
                    {labelBase}
                    {lastProgressOrStart.detail ? ` — ${lastProgressOrStart.detail}` : ''}
                  </span>
                </span>
              }
            />
            {warnings.map((warning, index) => (
              <p key={index} className="text-sm text-warning">
                {warning.message}
              </p>
            ))}
          </div>
        )
      })}

      {cancellable && onCancel && (
        <div className="flex justify-end">
          <AppButton
            type="button"
            variant="outline"
            size="sm"
            icon={Square}
            disabled={cancelling}
            onClick={onCancel}
          >
            {cancelling ? 'Cancelando…' : 'Cancelar'}
          </AppButton>
        </div>
      )}
    </div>
  )
}
