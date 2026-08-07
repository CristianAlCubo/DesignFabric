import { useState } from 'react'
import { CircleAlert } from 'lucide-react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'

import {
  StickerResultView,
  suggestedStickerName
} from '../../core/imaging/StickerResultView'
import type { StickerResult } from '../../core/api/types'

interface ResultsGalleryProps {
  results: StickerResult[]
  backendBaseUrl: string
}

/** Grilla de resultados de un job batch: una imagen (o el error) por prompt generado. */
export function ResultsGallery({ results, backendBaseUrl }: ResultsGalleryProps) {
  const [focused, setFocused] = useState<StickerResult | null>(null)

  return (
    <TooltipProvider>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(148px,1fr))] gap-3">
        {results.map((result, index) => (
          <figure key={index} className="m-0 flex min-w-0 flex-col gap-2">
            {result.success && result.image_url ? (
              <button
                type="button"
                className="overflow-hidden rounded-lg border border-border bg-checker-a text-left transition-opacity hover:opacity-90 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                onClick={() => setFocused(result)}
              >
                <img
                  src={`${backendBaseUrl}${result.image_url}`}
                  alt={result.prompt}
                  className="aspect-square w-full object-contain"
                />
              </button>
            ) : (
              <Alert variant="destructive" className="aspect-square items-center justify-center">
                <CircleAlert />
                <AlertDescription className="line-clamp-4">
                  {result.error ?? 'Error'}
                </AlertDescription>
              </Alert>
            )}
            <figcaption className="flex min-w-0 items-start gap-1.5">
              <Badge variant="secondary" className="shrink-0 tabular-nums">
                {index + 1}
              </Badge>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="line-clamp-2 min-w-0 flex-1 text-xs text-muted-foreground">
                    {result.prompt || 'Sin prompt'}
                  </span>
                </TooltipTrigger>
                {result.prompt ? (
                  <TooltipContent className="max-w-xs text-pretty">{result.prompt}</TooltipContent>
                ) : null}
              </Tooltip>
            </figcaption>
          </figure>
        ))}
      </div>

      <Dialog open={focused !== null} onOpenChange={(open) => !open && setFocused(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Sticker</DialogTitle>
            <DialogDescription className="text-pretty">{focused?.prompt}</DialogDescription>
          </DialogHeader>
          {focused?.success && focused.image_url ? (
            <StickerResultView
              imageUrl={`${backendBaseUrl}${focused.image_url}`}
              alt={focused.prompt}
              exportName={suggestedStickerName(focused.prompt, focused.image_url)}
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  )
}
