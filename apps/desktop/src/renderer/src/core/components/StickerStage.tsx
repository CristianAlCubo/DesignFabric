import type { ReactNode } from 'react'
import { ImageIcon, LoaderCircle } from 'lucide-react'

import { cn } from '@/lib/utils'

interface StickerStageProps {
  children?: ReactNode
  emptyLabel: string
  emptyHint?: string
  isBusy?: boolean
  busyLabel?: string
  className?: string
}

/** Lienzo tipo mesa de corte: empty / generando / resultado. */
export function StickerStage({
  children,
  emptyLabel,
  emptyHint,
  isBusy = false,
  busyLabel = 'Generando…',
  className
}: StickerStageProps) {
  const hasContent = Boolean(children)

  return (
    <div
      className={cn(
        'image-frame relative min-h-[280px] flex-1',
        !hasContent && 'items-center justify-center',
        className
      )}
    >
      {hasContent ? (
        <div className="absolute inset-0 flex min-h-0 flex-col overflow-auto p-4">{children}</div>
      ) : (
        <div className="flex max-w-sm flex-col items-center gap-3 px-6 text-center">
          {isBusy ? (
            <LoaderCircle className="size-8 animate-spin text-muted-foreground" aria-hidden />
          ) : (
            <ImageIcon className="size-8 text-muted-foreground" aria-hidden />
          )}
          <p className="text-sm font-medium text-foreground">
            {isBusy ? busyLabel : emptyLabel}
          </p>
          {!isBusy && emptyHint ? (
            <p className="text-sm text-muted-foreground text-pretty">{emptyHint}</p>
          ) : null}
        </div>
      )}
    </div>
  )
}
