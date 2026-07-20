/**
 * Panel de progreso de un job: agrupa los eventos WebSocket por fase
 * (generación de prompts / generación de imágenes), replicando visualmente
 * las barras `rich` que muestra el CLI. Genérico: reutilizado por las
 * features `designfabric-batch` y `designfabric-single`.
 */

import { useJobProgress } from '../hooks/useJobProgress'
import { ProgressBar } from './ProgressBar'

interface JobProgressPanelProps {
  jobId: string | null
}

const PHASE_LABELS: Record<string, string> = {
  prompt_generation: '🧠 Generación de prompts',
  image_generation: '🎨 Generación de imágenes'
}

export function JobProgressPanel({ jobId }: JobProgressPanelProps) {
  const { events } = useJobProgress(jobId)

  if (!jobId || events.length === 0) return null

  const phases = Array.from(new Set(events.map((event) => event.phase)))

  return (
    <div className="job-progress-panel">
      {phases.map((phase) => {
        const phaseEvents = events.filter((event) => event.phase === phase)
        const lastProgressOrStart = [...phaseEvents].reverse().find((e) => e.total !== null) ?? phaseEvents[0]
        const warnings = phaseEvents.filter((event) => event.type === 'warning')

        return (
          <div key={phase} className="job-progress-panel__phase">
            <ProgressBar
              current={lastProgressOrStart.current ?? 0}
              total={lastProgressOrStart.total ?? 0}
              label={`${PHASE_LABELS[phase] ?? phase}${
                lastProgressOrStart.detail ? ` — ${lastProgressOrStart.detail}` : ''
              }`}
            />
            {warnings.map((warning, index) => (
              <p key={index} className="text-sm text-warning">
                ⚠ {warning.message}
              </p>
            ))}
          </div>
        )
      })}
    </div>
  )
}
