import { Percent } from 'lucide-react'

import { cn } from '@/lib/utils'

import type { SizeRow } from '@shared/multiExportPresets'

interface SizeSwatchProps {
  row: Pick<SizeRow, 'mode' | 'width' | 'height' | 'percent'>
  size?: number
  className?: string
}

const MIN_RATIO = 1 / 3
const MAX_RATIO = 3

/**
 * Solo hay proporción real que mostrar cuando el modo es px y ambas dimensiones están
 * definidas — un porcentaje, o un px con un solo lado fijo, dependen de la imagen de origen
 * (que varía por archivo en un lote), así que no tienen una forma única que dibujar.
 */
function resolveRatio(row: SizeSwatchProps['row']): number | null {
  if (row.mode !== 'px') return null
  const { width, height } = row
  if (typeof width !== 'number' || width <= 0) return null
  if (typeof height !== 'number' || height <= 0) return null
  return Math.min(MAX_RATIO, Math.max(MIN_RATIO, width / height))
}

/** Miniatura de proporción de una fila de tamaño — el elemento de firma de esta feature. */
export function SizeSwatch({ row, size = 32, className }: SizeSwatchProps) {
  const ratio = resolveRatio(row)

  return (
    <div
      aria-hidden
      className={cn(
        'flex shrink-0 items-center justify-center rounded-sm bg-muted/40',
        ratio !== null ? 'border border-border' : 'border border-dashed border-border',
        className
      )}
      style={{ width: size, height: size }}
    >
      {ratio !== null ? (
        <div
          className="border border-foreground/40 bg-foreground/15"
          style={ratio >= 1 ? { width: '78%', aspectRatio: ratio } : { height: '78%', aspectRatio: ratio }}
        />
      ) : row.mode === 'percent' && typeof row.percent === 'number' ? (
        <span className="text-[9px] leading-none font-medium text-muted-foreground">
          {Math.round(row.percent)}%
        </span>
      ) : (
        <Percent className="size-3 text-muted-foreground" strokeWidth={2} />
      )}
    </div>
  )
}
