/**
 * Store Zustand del feature "Imagen única". Persiste formulario y jobId al
 * desmontar el panel (navegación entre secciones/tabs).
 */
import { create } from 'zustand'

import type { ImageProviderId } from '../../core/api/types'

interface GenerationSingleState {
  prompt: string
  applyStyleSuffix: boolean
  imageProvider: ImageProviderId
  /** Evita pisar la selección del usuario al rehidratar el catálogo. */
  providerInitialized: boolean

  jobId: string | null
  submitError: string | null

  setPrompt: (prompt: string) => void
  setApplyStyleSuffix: (value: boolean) => void
  setImageProvider: (id: ImageProviderId) => void
  ensureImageProviderDefault: (id: ImageProviderId) => void
  setJobId: (jobId: string | null) => void
  setSubmitError: (error: string | null) => void
}

export const useGenerationSingleStore = create<GenerationSingleState>((set, get) => ({
  prompt: '',
  applyStyleSuffix: true,
  imageProvider: 'test',
  providerInitialized: false,

  jobId: null,
  submitError: null,

  setPrompt: (prompt) => set({ prompt }),
  setApplyStyleSuffix: (applyStyleSuffix) => set({ applyStyleSuffix }),
  setImageProvider: (imageProvider) => set({ imageProvider }),

  ensureImageProviderDefault: (id) => {
    if (get().providerInitialized) return
    set({ imageProvider: id, providerInitialized: true })
  },

  setJobId: (jobId) => set({ jobId, submitError: null }),
  setSubmitError: (submitError) => set({ submitError })
}))
