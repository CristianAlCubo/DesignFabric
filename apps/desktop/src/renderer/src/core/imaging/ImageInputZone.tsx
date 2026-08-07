import type { LucideIcon } from 'lucide-react'
import { ImagePlus } from 'lucide-react'

import { cn } from '@/lib/utils'

import { AppButton } from '../components/AppButton'
import { ImageViewer } from './ImageViewer'
import type { ImageSource } from './imageSource'
import { useImageSource } from './useImageSource'

interface ImageInputZoneProps {
  /** Entrada actual (ruta + preview) que provee el store de la feature. */
  path: string | null
  previewUrl: string | null
  /** El store aplica la fuente adquirida a su estado. */
  onSource: (source: ImageSource) => void | Promise<void>
  onError?: (message: string) => void
  disabled?: boolean
  alt: string
  emptyLabel: string
  selectLabel?: string
  selectIcon?: LucideIcon
  /** Id de esta pestaña, para recibir transferencias de otras pantallas. */
  tabId?: string
}

/**
 * Zona de entrada de imagen unificada: botón de selección + hint de ruta + visor,
 * con los tres orígenes globales (diálogo, portapapeles Ctrl+V, drag & drop) y
 * consumo de transferencias entre pestañas concentrados en un solo lugar.
 *
 * Renderiza solo el contenido interno de la columna (no el `<section>`/`<h2>`),
 * para que cada panel conserve su encabezado y su layout de columnas.
 */
export function ImageInputZone({
  path,
  previewUrl,
  onSource,
  onError,
  disabled = false,
  alt,
  emptyLabel,
  selectLabel = 'Seleccionar imagen',
  selectIcon = ImagePlus,
  tabId
}: ImageInputZoneProps) {
  const { openDialog, handleDrop, handleDragOver, handleDragLeave, isDragOver } = useImageSource({
    currentPath: path,
    onSource,
    onError,
    disabled,
    tabId
  })

  return (
    <>
      <AppButton
        type="button"
        variant="outline"
        icon={selectIcon}
        onClick={() => void openDialog()}
        disabled={disabled}
      >
        {selectLabel}
      </AppButton>
      {path ? <p className="path-hint">{path}</p> : null}
      <div
        className={cn(
          'image-input-zone__viewport',
          isDragOver && 'image-input-zone__viewport--dragover'
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <ImageViewer src={previewUrl} alt={alt} emptyLabel={emptyLabel} />
      </div>
    </>
  )
}
