/** Estado de edición y guardado de plantillas de prenda. */
import { create } from 'zustand'

import { apiPost, getBackendBaseUrl, waitForBackendReady } from '../../core/api/httpClient'
import type { ImageSource } from '../../core/imaging/imageSource'

export type Point = [number, number]
type Corners = [Point, Point, Point, Point]

interface PreparationResponse {
  base_size: [number, number]
  mask_data_url: string
  shading_data_url: string
  displacement_data_url: string
  suggested_corners: Corners
}

interface TemplateSummary {
  id: string
  name: string
  thumbnail_url: string
  garment_colors: Record<string, string>
  max_print_cm: [number, number]
  px_per_cm: number
  base_size: [number, number]
}

interface TemplateState {
  photoPath: string | null
  photoPreview: string | null
  name: string
  id: string
  baseSize: [number, number] | null
  corners: Corners | null
  maskDataUrl: string | null
  shadingDataUrl: string | null
  displacementDataUrl: string | null
  pxPerCm: number
  chestWidthCm: number
  maxPrintWidthCm: number
  maxPrintHeightCm: number
  displacementStrengthPx: number
  shadingStrength: number
  highlightStrength: number
  isPreparing: boolean
  isSaving: boolean
  savedTemplate: TemplateSummary | null
  error: string | null
  setPhotoSource: (source: ImageSource) => void
  setName: (value: string) => void
  setId: (value: string) => void
  setCorners: (corners: Corners) => void
  setPxPerCm: (value: number) => void
  setChestWidthCm: (value: number) => void
  setMaxPrintWidthCm: (value: number) => void
  setMaxPrintHeightCm: (value: number) => void
  setDisplacementStrengthPx: (value: number) => void
  setShadingStrength: (value: number) => void
  setHighlightStrength: (value: number) => void
  prepare: (corners?: Corners) => Promise<void>
  save: () => Promise<void>
  setError: (message: string | null) => void
}

let prepareSeq = 0

function basename(path: string): string {
  return path.split(/[/\\]/).at(-1) ?? path
}

function templateId(name: string): string {
  return name
    .replace(/\.[^.]+$/, '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 64)
}

export const useMockupTemplateStore = create<TemplateState>((set, get) => ({
  photoPath: null,
  photoPreview: null,
  name: '',
  id: '',
  baseSize: null,
  corners: null,
  maskDataUrl: null,
  shadingDataUrl: null,
  displacementDataUrl: null,
  pxPerCm: 38.5,
  chestWidthCm: 28,
  maxPrintWidthCm: 30,
  maxPrintHeightCm: 40,
  displacementStrengthPx: 6,
  shadingStrength: 0.5,
  highlightStrength: 0.3,
  isPreparing: false,
  isSaving: false,
  savedTemplate: null,
  error: null,

  setPhotoSource: (source) => {
    const name = basename(source.path).replace(/\.[^.]+$/, '')
    set({
      photoPath: source.path,
      photoPreview: source.previewUrl,
      name,
      id: templateId(name),
      baseSize: null,
      corners: null,
      maskDataUrl: null,
      shadingDataUrl: null,
      displacementDataUrl: null,
      savedTemplate: null,
      error: null
    })
  },
  setName: (name) => set({ name, savedTemplate: null }),
  setId: (id) => set({ id, savedTemplate: null }),
  setCorners: (corners) => set({ corners, savedTemplate: null }),
  setPxPerCm: (pxPerCm) => set({ pxPerCm, savedTemplate: null }),
  setChestWidthCm: (chestWidthCm) => set({ chestWidthCm }),
  setMaxPrintWidthCm: (maxPrintWidthCm) => set({ maxPrintWidthCm, savedTemplate: null }),
  setMaxPrintHeightCm: (maxPrintHeightCm) => set({ maxPrintHeightCm, savedTemplate: null }),
  setDisplacementStrengthPx: (displacementStrengthPx) =>
    set({ displacementStrengthPx, savedTemplate: null }),
  setShadingStrength: (shadingStrength) => set({ shadingStrength, savedTemplate: null }),
  setHighlightStrength: (highlightStrength) => set({ highlightStrength, savedTemplate: null }),
  setError: (error) => set({ error }),

  prepare: async (givenCorners) => {
    const { photoPath, corners } = get()
    if (!photoPath) return
    const seq = ++prepareSeq
    set({ isPreparing: true, error: null })
    try {
      const result = await apiPost<
        { photo_path: string; corners?: Corners },
        PreparationResponse
      >('/api/mockups/templates/prepare', {
        photo_path: photoPath,
        ...(givenCorners ?? corners ? { corners: givenCorners ?? corners! } : {})
      })
      if (seq !== prepareSeq) return
      set({
        baseSize: result.base_size,
        corners: givenCorners ?? get().corners ?? result.suggested_corners,
        maskDataUrl: result.mask_data_url,
        shadingDataUrl: result.shading_data_url,
        displacementDataUrl: result.displacement_data_url
      })
    } catch (err) {
      if (seq !== prepareSeq) return
      set({ error: err instanceof Error ? err.message : 'No se pudo preparar la máscara.' })
    } finally {
      if (seq === prepareSeq) set({ isPreparing: false })
    }
  },

  save: async () => {
    const {
      photoPath,
      name,
      id,
      corners,
      pxPerCm,
      maxPrintWidthCm,
      maxPrintHeightCm,
      displacementStrengthPx,
      shadingStrength,
      highlightStrength,
      maskDataUrl,
      isSaving
    } = get()
    if (!photoPath || !corners || isSaving) return
    if (!/^[a-z0-9][a-z0-9-]{1,63}$/.test(id)) {
      set({ error: 'El ID debe tener 2–64 caracteres: minúsculas, números y guiones.' })
      return
    }
    if (!name.trim() || pxPerCm <= 0 || maxPrintWidthCm <= 0 || maxPrintHeightCm <= 0) {
      set({ error: 'Completa el nombre y las medidas con valores mayores que cero.' })
      return
    }
    set({ isSaving: true, error: null })
    try {
      await waitForBackendReady()
      const baseUrl = await getBackendBaseUrl()
      const response = await fetch(`${baseUrl}/api/mockups/templates/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          photo_path: photoPath,
          name: name.trim(),
          corners,
          px_per_cm: pxPerCm,
          max_print_cm: [maxPrintWidthCm, maxPrintHeightCm],
          default_anchor: 'top-center',
          displacement_strength_px: displacementStrengthPx,
          shading_strength: shadingStrength,
          highlight_strength: highlightStrength,
          garment_colors: { blanco: '#FFFFFF', negro: '#1A1A1A', rojo: '#C92F3A' },
          dark_garment_colors: ['negro'],
          ...(maskDataUrl ? { mask_data_url: maskDataUrl } : {})
        })
      })
      if (!response.ok) throw new Error(`PUT /api/mockups/templates/${id} → ${response.status}`)
      const savedTemplate = (await response.json()) as TemplateSummary
      set({ savedTemplate })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo guardar la plantilla.' })
    } finally {
      set({ isSaving: false })
    }
  }
}))
