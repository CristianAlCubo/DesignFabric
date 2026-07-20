/**
 * Store Zustand del feature "Generación por lotes". Persiste formulario y
 * jobId al desmontar el panel (navegación entre secciones/tabs).
 */
import { create } from 'zustand'

import type { ImageProviderId, LlmProviderId } from '../../core/api/types'

interface GenerationBatchState {
  numImages: number
  ollamaModel: string
  llmProvider: LlmProviderId
  imageProvider: ImageProviderId
  /** Evita pisar la selección del usuario al rehidratar el catálogo. */
  providersInitialized: boolean

  jobId: string | null
  submitError: string | null

  setNumImages: (n: number) => void
  setOllamaModel: (model: string) => void
  setLlmProvider: (id: LlmProviderId) => void
  setImageProvider: (id: ImageProviderId) => void
  ensureProviderDefaults: (llmId: LlmProviderId, imageId: ImageProviderId) => void
  ensureOllamaModel: (models: string[]) => void
  setJobId: (jobId: string | null) => void
  setSubmitError: (error: string | null) => void
}

export const useGenerationBatchStore = create<GenerationBatchState>((set, get) => ({
  numImages: 1,
  ollamaModel: 'gemma3:4b',
  llmProvider: 'test',
  imageProvider: 'test',
  providersInitialized: false,

  jobId: null,
  submitError: null,

  setNumImages: (numImages) => set({ numImages }),
  setOllamaModel: (ollamaModel) => set({ ollamaModel }),
  setLlmProvider: (llmProvider) => set({ llmProvider }),
  setImageProvider: (imageProvider) => set({ imageProvider }),

  ensureProviderDefaults: (llmId, imageId) => {
    if (get().providersInitialized) return
    set({ llmProvider: llmId, imageProvider: imageId, providersInitialized: true })
  },

  ensureOllamaModel: (models) => {
    if (models.length === 0) return
    const current = get().ollamaModel
    if (!models.includes(current)) {
      set({ ollamaModel: models[0] })
    }
  },

  setJobId: (jobId) => set({ jobId, submitError: null }),
  setSubmitError: (submitError) => set({ submitError })
}))
