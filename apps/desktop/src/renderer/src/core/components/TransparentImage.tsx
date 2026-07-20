import { useState, type ReactNode } from 'react'
import { Minus, Plus, Scan } from 'lucide-react'

import { AppButton } from './AppButton'
import { useImageViewport } from '../hooks/useImageViewport'

interface TransparentImageProps {
  src: string | null
  alt: string
  emptyLabel: string
  durationSeconds?: number | null
  /**
   * Acciones específicas de la feature (ej. "Exportar", "Enviar a escalado"),
   * renderizadas debajo del visor solo cuando hay una imagen cargada. El
   * visor en sí es puramente presentacional — no sabe nada de exportar
   * archivos ni de cambiar de tab, eso lo decide cada feature.
   */
  actions?: ReactNode
}

function formatDuration(seconds: number): string {
  return `(${seconds.toFixed(2)} s)`
}

/** Visor de imagen con zoom/pan (compartido entre remove-background y scale). */
export function TransparentImage({
  src,
  alt,
  emptyLabel,
  durationSeconds = null,
  actions
}: TransparentImageProps) {
  const [size, setSize] = useState<{ width: number; height: number; src: string } | null>(null)

  const visibleSize = src && size?.src === src ? size : null
  const hasImage = Boolean(src && visibleSize)

  const {
    containerRef,
    viewport,
    isPanning,
    zoomPercent,
    zoomIn,
    zoomOut,
    resetView,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handlePointerCancel,
    handleDoubleClick
  } = useImageViewport(hasImage, visibleSize?.width ?? null, visibleSize?.height ?? null)

  const frameClassName = [
    'image-frame',
    hasImage ? 'image-frame--interactive' : '',
    isPanning ? 'image-frame--panning' : ''
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="image-viewer">
      <div
        ref={containerRef}
        className={frameClassName}
        onPointerDown={hasImage ? handlePointerDown : undefined}
        onPointerMove={hasImage ? handlePointerMove : undefined}
        onPointerUp={hasImage ? handlePointerUp : undefined}
        onPointerCancel={hasImage ? handlePointerCancel : undefined}
        onDoubleClick={hasImage ? handleDoubleClick : undefined}
      >
        {src ? (
          <div
            className={visibleSize ? 'image-frame__stage' : 'image-frame__stage image-frame__stage--pending'}
            style={
              visibleSize
                ? {
                    transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`
                  }
                : undefined
            }
          >
            <img
              key={src}
              className="image-frame__img"
              src={src}
              alt={alt}
              draggable={false}
              onLoad={(event) => {
                const { naturalWidth, naturalHeight } = event.currentTarget
                if (naturalWidth > 0 && naturalHeight > 0) {
                  setSize({ width: naturalWidth, height: naturalHeight, src })
                }
              }}
            />
          </div>
        ) : (
          <p className="image-frame__empty">{emptyLabel}</p>
        )}

        {hasImage ? (
          <div
            className="image-frame__toolbar"
            role="toolbar"
            aria-label="Controles de zoom"
            onPointerDown={(event) => event.stopPropagation()}
            onDoubleClick={(event) => event.stopPropagation()}
          >
            <AppButton
              type="button"
              variant="secondary"
              size="icon-xs"
              icon={Minus}
              onClick={zoomOut}
              aria-label="Alejar"
              title="Alejar"
            />
            <AppButton
              type="button"
              variant="secondary"
              size="xs"
              icon={Scan}
              className="min-w-12 tabular-nums"
              onClick={resetView}
              aria-label="Ajustar a la vista"
              title="Ajustar a la vista"
            >
              {zoomPercent}%
            </AppButton>
            <AppButton
              type="button"
              variant="secondary"
              size="icon-xs"
              icon={Plus}
              onClick={zoomIn}
              aria-label="Acercar"
              title="Acercar"
            />
          </div>
        ) : null}
      </div>

      {visibleSize ? (
        <div className="image-viewer__meta" aria-live="polite">
          <p className="image-viewer__size">
            {visibleSize.width} × {visibleSize.height}
          </p>
          {durationSeconds !== null && Number.isFinite(durationSeconds) ? (
            <p className="image-viewer__duration">{formatDuration(durationSeconds)}</p>
          ) : null}
        </div>
      ) : null}

      {src && actions ? <div className="image-viewer__actions">{actions}</div> : null}
    </div>
  )
}
