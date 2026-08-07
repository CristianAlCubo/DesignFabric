import { useEffect, type ReactNode } from 'react'
import { Download, Send } from 'lucide-react'

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuItem,
  ContextMenuTrigger
} from '@/components/ui/context-menu'

import { AppButton } from '../components/AppButton'
import { featureRegistry } from '../registry/featureRegistry'
import { useImageTransferStore } from '../state/imageTransferStore'
import { ImageViewer } from './ImageViewer'
import { useImageExport } from './useImageExport'

interface ImageResultViewProps {
  /** URL de la imagen servida por el backend (o `null` mientras no hay resultado). */
  src: string | null
  alt: string
  emptyLabel: string
  durationSeconds?: number | null
  /**
   * Nombre sugerido para exportar. Si se provee, se muestra el botón "Exportar".
   * Puede ser una función para calcularlo de forma perezosa (ej. depende del formato).
   */
  exportName?: string | (() => string)
  onExportError?: (message: string) => void
  /** Acciones adicionales de la feature (ej. botones extra bajo el visor). */
  extraActions?: ReactNode
  /**
   * Ruta en disco del resultado (necesaria para transferirlo como entrada de otra
   * pantalla). Junto con `sendTargets` habilita el menú contextual «Enviar a:».
   */
  sourcePath?: string | null
  /**
   * Ids de las pestañas destino a las que ESTA instancia puede enviar su resultado.
   * Cada pantalla decide su propia lista; no hay una global fija. Sin targets (o sin
   * resultado) no se ofrece la acción de enviar.
   */
  sendTargets?: string[]
}

/**
 * Vista de resultado de imagen unificada: el visor compartido más la exportación
 * estándar (`useImageExport`) y un menú contextual «Enviar a:» (click derecho) que
 * transfiere el resultado como entrada de otra pantalla vía el bus de transferencia.
 */
export function ImageResultView({
  src,
  alt,
  emptyLabel,
  durationSeconds = null,
  exportName,
  onExportError,
  extraActions,
  sourcePath = null,
  sendTargets
}: ImageResultViewProps) {
  const { exportImage, isExporting, error } = useImageExport()
  const sendToTab = useImageTransferStore((state) => state.send)

  useEffect(() => {
    if (error) onExportError?.(error)
  }, [error, onExportError])

  const resolveName = (): string =>
    typeof exportName === 'function' ? exportName() : (exportName ?? 'imagen.png')

  const actions =
    src && (exportName !== undefined || extraActions) ? (
      <>
        {exportName !== undefined ? (
          <AppButton
            type="button"
            variant="outline"
            icon={Download}
            onClick={() => void exportImage(src, resolveName())}
            disabled={isExporting}
          >
            {isExporting ? 'Exportando…' : 'Exportar'}
          </AppButton>
        ) : null}
        {extraActions}
      </>
    ) : undefined

  const viewer = (
    <ImageViewer
      src={src}
      alt={alt}
      emptyLabel={emptyLabel}
      durationSeconds={durationSeconds}
      actions={actions}
    />
  )

  // Resuelve los targets declarados a pestañas que aún existen en el registro.
  const targets = (sendTargets ?? [])
    .map((tabId) => {
      const tab = featureRegistry.get(tabId)
      return tab ? { id: tabId, label: tab.label } : null
    })
    .filter((target): target is { id: string; label: string } => target !== null)

  const canSend = Boolean(src && sourcePath) && targets.length > 0

  if (!canSend) return viewer

  return (
    <ContextMenu>
      {/* Envoltorio DOM real: `asChild` sobre el componente `ImageViewer` no
          reenviaría `onContextMenu` a su raíz. El div llena la columna igual que el visor. */}
      <ContextMenuTrigger asChild>
        <div className="flex min-h-0 flex-1 flex-col">{viewer}</div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuSub>
          <ContextMenuSubTrigger>
            <Send />
            Enviar a:
          </ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {targets.map((target) => (
              <ContextMenuItem
                key={target.id}
                onSelect={() => {
                  if (src && sourcePath) {
                    sendToTab(target.id, {
                      path: sourcePath,
                      previewUrl: src,
                      origin: 'transfer'
                    })
                  }
                }}
              >
                {target.label}
              </ContextMenuItem>
            ))}
          </ContextMenuSubContent>
        </ContextMenuSub>
      </ContextMenuContent>
    </ContextMenu>
  )
}
