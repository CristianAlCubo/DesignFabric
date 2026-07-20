import { Progress } from '@/components/ui/progress'

interface ProgressBarProps {
  current: number
  total: number
  label?: string
}

/** Barra de progreso simple, reutilizada por las vistas batch y de imagen única. */
export function ProgressBar({ current, total, label }: ProgressBarProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0

  return (
    <div className="flex flex-col gap-1.5">
      {label ? <div className="text-sm text-muted-foreground">{label}</div> : null}
      <Progress value={percent} />
      <div className="text-sm text-muted-foreground tabular-nums">
        {current} / {total}
      </div>
    </div>
  )
}
