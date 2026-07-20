import type { StickerResult } from '../../core/api/types'

interface ResultsGalleryProps {
  results: StickerResult[]
  backendBaseUrl: string
}

/** Grilla de resultados de un job batch: una imagen (o el error) por prompt generado. */
export function ResultsGallery({ results, backendBaseUrl }: ResultsGalleryProps) {
  return (
    <div className="results-gallery">
      {results.map((result, index) => (
        <figure key={index} className="results-gallery__item">
          {result.success && result.image_url ? (
            <img src={`${backendBaseUrl}${result.image_url}`} alt={result.prompt} />
          ) : (
            <div className="results-gallery__error">✘ {result.error}</div>
          )}
          <figcaption>{result.prompt}</figcaption>
        </figure>
      ))}
    </div>
  )
}
