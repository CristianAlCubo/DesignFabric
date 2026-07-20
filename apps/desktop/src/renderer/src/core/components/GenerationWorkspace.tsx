import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface GenerationWorkspaceProps {
  title: string
  description?: string
  controls: ReactNode
  stage: ReactNode
  className?: string
}

/** Shell compartido de generación IA: rail de controles + stage de stickers. */
export function GenerationWorkspace({
  title,
  description,
  controls,
  stage,
  className
}: GenerationWorkspaceProps) {
  return (
    <div
      className={cn(
        'grid h-full min-h-0 grid-cols-1 gap-5 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)]',
        className
      )}
    >
      <aside className="flex min-h-0 flex-col gap-4 overflow-auto rounded-lg border border-border bg-card p-4">
        <header className="flex flex-col gap-1">
          <h2 className="text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            {title}
          </h2>
          {description ? (
            <p className="text-sm text-muted-foreground text-pretty">{description}</p>
          ) : null}
        </header>
        {controls}
      </aside>
      <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-card">
        {stage}
      </section>
    </div>
  )
}
