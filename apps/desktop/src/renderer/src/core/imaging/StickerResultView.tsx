import { useEffect } from 'react'
import { Download } from 'lucide-react'

import { AppButton } from '../components/AppButton'
import { useImageExport } from './useImageExport'

interface StickerResultViewProps {
  /** URL completa de la imagen servida por el backend. */
  imageUrl: string
  alt: string
  /** Nombre sugerido al exportar. */
  exportName: string
  /** Texto bajo la imagen (ej. el prompt final usado). */
  caption?: string
  onExportError?: (message: string) => void
}

/**
 * Vista de resultado para imágenes generadas por IA (stickers): figura sobre fondo
 * de tablero de ajedrez + exportación estándar (`useImageExport`). Es la base común
 * del lado de salida de la IA — la usan `SingleImageResult` y el diálogo de
 * `ResultsGallery`. No incluye el visor con zoom/pan porque estos resultados se
 * muestran a tamaño contenido, no se editan.
 */
export function StickerResultView({
  imageUrl,
  alt,
  exportName,
  caption,
  onExportError
}: StickerResultViewProps) {
  const { exportImage, isExporting, error } = useImageExport()

  useEffect(() => {
    if (error) onExportError?.(error)
  }, [error, onExportError])

  return (
    <figure className="m-auto flex w-full max-w-lg flex-col gap-3">
      <div className="mx-auto w-fit max-w-full overflow-hidden rounded-lg border border-border bg-checker-a">
        <img
          src={imageUrl}
          alt={alt}
          className="block max-h-[min(70vh,560px)] w-auto max-w-full object-contain"
        />
      </div>
      {caption ? (
        <figcaption className="text-sm text-muted-foreground text-pretty">{caption}</figcaption>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <AppButton
          type="button"
          variant="outline"
          icon={Download}
          onClick={() => void exportImage(imageUrl, exportName)}
          disabled={isExporting}
        >
          {isExporting ? 'Exportando…' : 'Exportar'}
        </AppButton>
      </div>
    </figure>
  )
}

/** Nombre de archivo sugerido para un sticker, derivado del prompt y la extensión de la URL. */
export function suggestedStickerName(prompt: string, imageUrl: string): string {
  const extMatch = imageUrl.match(/\.(png|jpe?g|webp|gif)(?:\?|$)/i)
  const ext = extMatch?.[1]?.toLowerCase() ?? 'png'
  const slug = prompt
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
  return `${slug || 'sticker'}.${ext === 'jpeg' ? 'jpg' : ext}`
}
