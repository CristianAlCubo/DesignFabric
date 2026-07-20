import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CircleAlert, Download } from 'lucide-react'

import { AppButton } from '../../core/components/AppButton'
import type { StickerResult } from '../../core/api/types'

interface SingleImageResultProps {
  result: StickerResult
  backendBaseUrl: string
}

function suggestedExportName(prompt: string, imageUrl: string): string {
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

/** Imagen resultante + prompt final usado (útil para ver si se aplicó el estilo sticker). */
export function SingleImageResult({ result, backendBaseUrl }: SingleImageResultProps) {
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  if (!result.success || !result.image_url) {
    return (
      <Alert variant="destructive" className="m-auto max-w-md">
        <CircleAlert />
        <AlertDescription>{result.error ?? 'Error desconocido'}</AlertDescription>
      </Alert>
    )
  }

  const imageSrc = `${backendBaseUrl}${result.image_url}`

  async function handleExport(): Promise<void> {
    if (isExporting || !result.image_url) return
    setIsExporting(true)
    setExportError(null)
    try {
      await window.designfabric.exportImage(
        imageSrc,
        suggestedExportName(result.prompt, result.image_url)
      )
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'No se pudo exportar la imagen.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <figure className="m-auto flex w-full max-w-lg flex-col gap-3">
      <div className="mx-auto w-fit max-w-full overflow-hidden rounded-lg border border-border bg-transparent">
        <img
          src={imageSrc}
          alt={result.prompt}
          className="block max-h-[min(70vh,560px)] w-auto max-w-full object-contain"
        />
      </div>
      <figcaption className="text-sm text-muted-foreground text-pretty">{result.prompt}</figcaption>
      <div className="flex flex-wrap items-center gap-2">
        <AppButton
          type="button"
          variant="outline"
          icon={Download}
          onClick={() => void handleExport()}
          disabled={isExporting}
        >
          {isExporting ? 'Exportando…' : 'Exportar'}
        </AppButton>
      </div>
      {exportError ? (
        <p className="text-sm text-destructive" role="alert">
          {exportError}
        </p>
      ) : null}
    </figure>
  )
}
