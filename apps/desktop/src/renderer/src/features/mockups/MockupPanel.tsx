import { useEffect, useState } from 'react'
import { Download, Loader2, Shirt, TriangleAlert } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'

import { AppButton } from '../../core/components/AppButton'
import { ImageInputZone } from '../../core/imaging/ImageInputZone'
import { ImageResultView } from '../../core/imaging/ImageResultView'
import { getBackendBaseUrl } from '../../core/api/httpClient'
import { useMockupStore } from './store'

const PREVIEW_DEBOUNCE_MS = 280

export function MockupPanel() {
  const [backendBaseUrl, setBackendBaseUrl] = useState<string | null>(null)
  const inputPath = useMockupStore((state) => state.inputPath)
  const inputPreview = useMockupStore((state) => state.inputPreview)
  const templates = useMockupStore((state) => state.templates)
  const selectedTemplateId = useMockupStore((state) => state.selectedTemplateId)
  const garmentColor = useMockupStore((state) => state.garmentColor)
  const printWidthCm = useMockupStore((state) => state.printWidthCm)
  const offsetXcm = useMockupStore((state) => state.offsetXcm)
  const offsetYcm = useMockupStore((state) => state.offsetYcm)
  const previewSrc = useMockupStore((state) => state.previewSrc)
  const previewSize = useMockupStore((state) => state.previewSize)
  const warnings = useMockupStore((state) => state.warnings)
  const isLoadingTemplates = useMockupStore((state) => state.isLoadingTemplates)
  const isPreviewing = useMockupStore((state) => state.isPreviewing)
  const isSaving = useMockupStore((state) => state.isSaving)
  const outputPath = useMockupStore((state) => state.outputPath)
  const outputUrl = useMockupStore((state) => state.outputUrl)
  const error = useMockupStore((state) => state.error)
  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId)

  const loadTemplates = useMockupStore((state) => state.loadTemplates)
  const setInputSource = useMockupStore((state) => state.setInputSource)
  const selectTemplate = useMockupStore((state) => state.selectTemplate)
  const setGarmentColor = useMockupStore((state) => state.setGarmentColor)
  const setPrintWidthCm = useMockupStore((state) => state.setPrintWidthCm)
  const setOffsetXcm = useMockupStore((state) => state.setOffsetXcm)
  const setOffsetYcm = useMockupStore((state) => state.setOffsetYcm)
  const refreshPreview = useMockupStore((state) => state.refreshPreview)
  const saveFullRes = useMockupStore((state) => state.saveFullRes)
  const setError = useMockupStore((state) => state.setError)

  useEffect(() => {
    void loadTemplates()
  }, [loadTemplates])

  useEffect(() => {
    void getBackendBaseUrl().then(setBackendBaseUrl).catch(() => setBackendBaseUrl(null))
  }, [])

  useEffect(() => {
    if (!inputPath || !selectedTemplateId || !garmentColor) return
    const handle = setTimeout(() => void refreshPreview(), PREVIEW_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [inputPath, selectedTemplateId, garmentColor, printWidthCm, offsetXcm, offsetYcm, refreshPreview])

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {error ? (
        <p className="error flex-none" role="alert">
          {error}
        </p>
      ) : null}

      <div className="columns columns--scale min-h-0 flex-1">
        <section className="column panel">
          <h2 className="column__title">Diseño</h2>
          <ImageInputZone
            path={inputPath}
            previewUrl={inputPreview}
            onSource={setInputSource}
            onError={setError}
            disabled={isSaving}
            tabId="mockups"
            alt="Diseño para aplicar en la prenda"
            emptyLabel="Selecciona, pega o arrastra un diseño con transparencia"
          />

          <div className="mt-4 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">Plantilla</h3>
              {isLoadingTemplates ? (
                <Loader2 className="size-4 animate-spin text-muted-foreground" aria-label="Cargando" />
              ) : null}
            </div>
            {templates.length ? (
              <div className="grid grid-cols-2 gap-2">
                {templates.map((template) => (
                  <button
                    type="button"
                    key={template.id}
                    aria-pressed={template.id === selectedTemplateId}
                    onClick={() => selectTemplate(template.id)}
                    disabled={isSaving}
                    className={`group overflow-hidden rounded-md border text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      template.id === selectedTemplateId
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-muted/60'
                    }`}
                  >
                    <div className="aspect-[4/3] overflow-hidden bg-muted">
                      <img
                        src={
                          /^https?:\/\//.test(template.thumbnail_url)
                            ? template.thumbnail_url
                            : backendBaseUrl
                              ? `${backendBaseUrl}${template.thumbnail_url}`
                              : undefined
                        }
                        alt=""
                        className="size-full object-cover"
                        loading="lazy"
                      />
                    </div>
                    <span className="block truncate px-2 py-1.5 text-xs font-medium">
                      {template.name}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {isLoadingTemplates
                  ? 'Cargando plantillas…'
                  : 'No hay plantillas disponibles. Crea una desde «Plantillas de mockup».'}
              </p>
            )}
          </div>
        </section>

        <section className="column panel panel--form overflow-y-auto">
          <h2 className="column__title">Impresión</h2>
          {selectedTemplate ? (
            <div className="flex flex-col gap-5">
              <Field>
                <FieldLabel htmlFor="mockup-garment-color">Color de prenda</FieldLabel>
                <Select
                  value={garmentColor}
                  onValueChange={setGarmentColor}
                  disabled={isSaving}
                >
                  <SelectTrigger id="mockup-garment-color" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(selectedTemplate.garment_colors).map(([name, color]) => (
                      <SelectItem key={name} value={name}>
                        <span
                          className="mr-2 inline-block size-3 rounded-full border border-border align-[-2px]"
                          style={{ backgroundColor: color }}
                        />
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field>
                <div className="flex items-baseline justify-between gap-3">
                  <FieldLabel htmlFor="mockup-print-width">Ancho de impresión</FieldLabel>
                  <span className="text-sm tabular-nums text-muted-foreground">
                    {printWidthCm.toFixed(1)} cm
                  </span>
                </div>
                <Slider
                  id="mockup-print-width"
                  min={0.5}
                  max={selectedTemplate.max_print_cm[0]}
                  step={0.1}
                  value={[Math.min(printWidthCm, selectedTemplate.max_print_cm[0])]}
                  onValueChange={(value) => setPrintWidthCm(value[0] ?? printWidthCm)}
                  disabled={isSaving}
                />
                <p className="text-xs text-muted-foreground">
                  Máximo {selectedTemplate.max_print_cm[0]} × {selectedTemplate.max_print_cm[1]} cm
                </p>
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field>
                  <FieldLabel htmlFor="mockup-offset-x">Desplazamiento X (cm)</FieldLabel>
                  <Input
                    id="mockup-offset-x"
                    type="number"
                    step="0.1"
                    value={offsetXcm}
                    onChange={(event) => setOffsetXcm(Number(event.target.value))}
                    disabled={isSaving}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="mockup-offset-y">Desplazamiento Y (cm)</FieldLabel>
                  <Input
                    id="mockup-offset-y"
                    type="number"
                    step="0.1"
                    value={offsetYcm}
                    onChange={(event) => setOffsetYcm(Number(event.target.value))}
                    disabled={isSaving}
                  />
                </Field>
              </div>
              <p className="text-xs text-muted-foreground">
                Tamaño físico calibrado a {selectedTemplate.px_per_cm.toFixed(1)} px/cm.
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Selecciona una plantilla para ajustar la impresión.
            </p>
          )}
        </section>

        <section className="column panel">
          <h2 className="column__title">
            Previsualización
            {isPreviewing ? (
              <Loader2 className="ml-2 inline size-4 animate-spin align-[-2px]" />
            ) : null}
          </h2>
          <ImageResultView
            src={outputUrl ?? previewSrc}
            alt="Previsualización del mockup"
            emptyLabel="El mockup aparecerá aquí"
            onExportError={setError}
            sourcePath={outputPath}
            sendTargets={[]}
          />

          {warnings.length > 0 ? (
            <Alert>
              <TriangleAlert />
              <AlertTitle>Revisa el diseño</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-4">
                  {warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          ) : null}

          {previewSize ? (
            <p className="text-xs text-muted-foreground">
              Vista {previewSize[0]} × {previewSize[1]} px · El archivo final se genera a resolución completa.
            </p>
          ) : null}
          <AppButton
            type="button"
            icon={isSaving ? Loader2 : outputPath ? Download : Shirt}
            iconClassName={isSaving ? 'animate-spin' : undefined}
            onClick={() => void saveFullRes()}
            disabled={!inputPath || !selectedTemplateId || isSaving}
            className="self-end"
          >
            {isSaving ? 'Generando…' : 'Guardar PNG'}
          </AppButton>
        </section>
      </div>
    </div>
  )
}
