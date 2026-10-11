/** Estado de la herramienta de composición determinista de mockups. */
import { create } from 'zustand'

import { apiGet, apiPost, getBackendBaseUrl } from '../../core/api/httpClient'
import { waitForJob } from '../../core/api/waitForJob'
import type { ImageSource } from '../../core/imaging/imageSource'

export interface MockupTemplateSummary {
  id: string
  name: string
  thumbnail_url: string
  garment_colors: Record<string, string>
  max_print_cm: [number, number]
  px_per_cm: number
  base_size: [number, number]
}

interface MockupPreviewResponse {
  image_data_url: string
  width: number
  height: number
  warnings: string[]
}

interface MockupJobResult {
  output_path: string
  image_url: string
}

interface MockupState {
  inputPath: string | null
  inputPreview: string | null
  templates: MockupTemplateSummary[]
  selectedTemplateId: string | null
  garmentColor: string
  printWidthCm: number
  offsetXcm: number
  offsetYcm: number
  previewSrc: string | null
  previewSize: [number, number] | null
  warnings: string[]
  isLoadingTemplates: boolean
  isPreviewing: boolean
  isSaving: boolean
  outputPath: string | null
  outputUrl: string | null
  error: string | null
  loadTemplates: () => Promise<void>
  setInputSource: (source: ImageSource) => void
  selectTemplate: (id: string) => void
  setPreferredTemplateId: (id: string) => void
  setGarmentColor: (color: string) => void
  setPrintWidthCm: (width: number) => void
  setOffsetXcm: (offset: number) => void
  setOffsetYcm: (offset: number) => void
  refreshPreview: () => Promise<void>
  saveFullRes: () => Promise<void>
  setError: (error: string | null) => void
}

let previewSeq = 0

function clearOutput() {
  return { outputPath: null, outputUrl: null }
}

export const useMockupStore = create<MockupState>((set, get) => ({
  inputPath: null,
  inputPreview: null,
  templates: [],
  selectedTemplateId: null,
  garmentColor: '',
  printWidthCm: 20,
  offsetXcm: 0,
  offsetYcm: 0,
  previewSrc: null,
  previewSize: null,
  warnings: [],
  isLoadingTemplates: false,
  isPreviewing: false,
  isSaving: false,
  outputPath: null,
  outputUrl: null,
  error: null,

  loadTemplates: async () => {
    set({ isLoadingTemplates: true, error: null })
    try {
      const response = await apiGet<{ templates: MockupTemplateSummary[] }>(
        '/api/mockups/templates'
      )
      const templates = response.templates
      const currentId = get().selectedTemplateId
      const selected = templates.find((template) => template.id === currentId) ?? templates[0]
      const color = selected
        ? Object.keys(selected.garment_colors).includes(get().garmentColor)
          ? get().garmentColor
          : Object.keys(selected.garment_colors)[0] ?? ''
        : ''
      set({
        templates,
        selectedTemplateId: selected?.id ?? null,
        garmentColor: color,
        printWidthCm: selected ? Math.min(get().printWidthCm, selected.max_print_cm[0]) : 20
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudieron cargar las plantillas.' })
    } finally {
      set({ isLoadingTemplates: false })
    }
  },

  setInputSource: (source) =>
    set({
      inputPath: source.path,
      inputPreview: source.previewUrl,
      previewSrc: null,
      previewSize: null,
      warnings: [],
      ...clearOutput(),
      error: null
    }),
  selectTemplate: (id) => {
    const template = get().templates.find((item) => item.id === id)
    if (!template) return
    set((state) => ({
      selectedTemplateId: id,
      garmentColor: Object.keys(template.garment_colors).includes(state.garmentColor)
        ? state.garmentColor
        : Object.keys(template.garment_colors)[0] ?? '',
      printWidthCm: Math.min(state.printWidthCm, template.max_print_cm[0]),
      ...clearOutput()
    }))
  },
  setPreferredTemplateId: (id) => set({ selectedTemplateId: id, ...clearOutput() }),
  setGarmentColor: (garmentColor) => set({ garmentColor, ...clearOutput() }),
  setPrintWidthCm: (printWidthCm) => set({ printWidthCm, ...clearOutput() }),
  setOffsetXcm: (offsetXcm) => set({ offsetXcm, ...clearOutput() }),
  setOffsetYcm: (offsetYcm) => set({ offsetYcm, ...clearOutput() }),
  setError: (error) => set({ error }),

  refreshPreview: async () => {
    const { inputPath, selectedTemplateId, garmentColor, printWidthCm, offsetXcm, offsetYcm } =
      get()
    if (!inputPath || !selectedTemplateId || !garmentColor || printWidthCm <= 0) return
    const seq = ++previewSeq
    set({ isPreviewing: true, error: null, ...clearOutput() })
    try {
      const result = await apiPost<
        {
          design_path: string
          template_id: string
          garment_color: string
          print_width_cm: number
          offset_cm: [number, number]
          max_side: number
        },
        MockupPreviewResponse
      >('/api/mockups/preview', {
        design_path: inputPath,
        template_id: selectedTemplateId,
        garment_color: garmentColor,
        print_width_cm: printWidthCm,
        offset_cm: [offsetXcm, offsetYcm],
        max_side: 1080
      })
      if (seq !== previewSeq) return
      set({
        previewSrc: result.image_data_url,
        previewSize: [result.width, result.height],
        warnings: result.warnings
      })
    } catch (err) {
      if (seq !== previewSeq) return
      set({ error: err instanceof Error ? err.message : 'No se pudo generar la previsualización.' })
    } finally {
      if (seq === previewSeq) set({ isPreviewing: false })
    }
  },

  saveFullRes: async () => {
    const { inputPath, selectedTemplateId, garmentColor, printWidthCm, offsetXcm, offsetYcm, isSaving } =
      get()
    if (!inputPath || !selectedTemplateId || !garmentColor || isSaving) return
    set({ isSaving: true, error: null, ...clearOutput() })
    try {
      const { job_id: jobId } = await apiPost<
        {
          design_path: string
          template_id: string
          garment_color: string
          print_width_cm: number
          offset_cm: [number, number]
        },
        { job_id: string }
      >('/api/mockups', {
        design_path: inputPath,
        template_id: selectedTemplateId,
        garment_color: garmentColor,
        print_width_cm: printWidthCm,
        offset_cm: [offsetXcm, offsetYcm]
      })
      const result = await waitForJob<MockupJobResult>(jobId)
      const baseUrl = await getBackendBaseUrl()
      await window.designfabric.exportImage(`${baseUrl}${result.image_url}`, 'mockup.png')
      set({
        outputPath: result.output_path,
        outputUrl: `${baseUrl}${result.image_url}`
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'No se pudo generar y guardar el mockup.' })
    } finally {
      set({ isSaving: false })
    }
  }
}))
