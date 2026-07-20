/** Resuelve (una vez) la URL base del backend, para construir URLs de imágenes servidas. */

import { useEffect, useState } from 'react'

import { getBackendBaseUrl } from '../../core/api/httpClient'

export function useBackendBaseUrl(): string | null {
  const [baseUrl, setBaseUrl] = useState<string | null>(null)

  useEffect(() => {
    getBackendBaseUrl().then(setBaseUrl)
  }, [])

  return baseUrl
}
