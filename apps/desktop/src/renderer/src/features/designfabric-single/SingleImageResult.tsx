import { Alert, AlertDescription } from '@/components/ui/alert'
import { CircleAlert } from 'lucide-react'

import {
  StickerResultView,
  suggestedStickerName
} from '../../core/imaging/StickerResultView'
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

  const imageSrc = `${backendBaseUrl}${result.image_url}`

  return (
    <StickerResultView
      imageUrl={imageSrc}
      alt={result.prompt}
      caption={result.prompt}
      exportName={suggestedStickerName(result.prompt, result.image_url)}
    />
  )
}
