import { useGenerationReadiness } from './useGenerationReadiness'
import type { GenerationProvidersResponse } from '../api/types'

/**
 * @deprecated Preferí `useGenerationReadiness` (catálogo derivado del probe).
 * Se mantiene como wrapper fino para no romper imports existentes.
 */
export function useGenerationProviders(): GenerationProvidersResponse | null {
  return useGenerationReadiness().catalog
}
