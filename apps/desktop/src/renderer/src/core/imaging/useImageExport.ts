/**
 * Hook que unifica la exportación de un resultado de imagen (guardar vía diálogo
 * nativo la imagen servida por el backend). Reemplaza las implementaciones
 * `exportOutput` duplicadas de cada store, con su estado `isExporting`/`error`.
 */
import { useCallback, useState } from 'react'

interface UseImageExportResult {
  exportImage: (sourceUrl: string, suggestedName: string) => Promise<void>
  isExporting: boolean
  error: string | null
}

export function useImageExport(): UseImageExportResult {
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const exportImage = useCallback(
    async (sourceUrl: string, suggestedName: string) => {
      if (isExporting) return
      setIsExporting(true)
      setError(null)
      try {
        await window.designfabric.exportImage(sourceUrl, suggestedName)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'No se pudo exportar la imagen.')
      } finally {
        setIsExporting(false)
      }
    },
    [isExporting]
  )

  return { exportImage, isExporting, error }
}
