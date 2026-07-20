import { Alert, AlertDescription } from '@/components/ui/alert'
import { CircleAlert } from 'lucide-react'

import type { StickerResult } from '../../core/api/types'

interface SingleImageResultProps {
  result: StickerResult
  backendBaseUrl: string
}

/** Imagen resultante + prompt final usado (útil para ver si se aplicó el estilo sticker). */
export function SingleImageResult({ result, backendBaseUrl }: SingleImageResultProps) {
  if (!result.success || !result.image_url) {
    return (
      <Alert variant="destructive" className="m-auto max-w-md">
        <CircleAlert />
        <AlertDescription>{result.error ?? 'Error desconocido'}</AlertDescription>
      </Alert>
    )
  }

  return (
    <figure className="m-auto flex w-full max-w-lg flex-col gap-3">
      <div className="overflow-hidden rounded-lg border border-border bg-checker-a shadow-sm">
        <img
          src={`${backendBaseUrl}${result.image_url}`}
          alt={result.prompt}
          className="mx-auto block max-h-[min(70vh,560px)] w-auto max-w-full object-contain"
        />
      </div>
      <figcaption className="text-sm text-muted-foreground text-pretty">{result.prompt}</figcaption>
    </figure>
  )
}
