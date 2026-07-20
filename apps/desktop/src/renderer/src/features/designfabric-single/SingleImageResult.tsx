import type { StickerResult } from '../../core/api/types'

interface SingleImageResultProps {
  result: StickerResult
  backendBaseUrl: string
}

/** Imagen resultante + prompt final usado (útil para ver si se aplicó el estilo sticker). */
export function SingleImageResult({ result, backendBaseUrl }: SingleImageResultProps) {
  if (!result.success || !result.image_url) {
    return <div className="single-image-result__error">✘ {result.error}</div>
  }

  return (
    <figure className="single-image-result">
      <img src={`${backendBaseUrl}${result.image_url}`} alt={result.prompt} />
      <figcaption>{result.prompt}</figcaption>
    </figure>
  )
}
