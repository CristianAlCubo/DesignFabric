import { useEffect, type ReactNode } from 'react'
import { CircleHelp, Download, FileImage, Info, Loader2, RotateCcw } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Slider } from '@/components/ui/slider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

import { AppButton } from '../../core/components/AppButton'
import { ImageInputZone } from '../../core/imaging/ImageInputZone'
import { ImageViewer } from '../../core/imaging/ImageViewer'
import {
  DEFAULT_PARAMS,
  useHalftoneStore,
  type DotShape,
  type HalftoneMethod,
  type HalftoneParams
} from './store'

/** Debounce (ms) del preview en vivo ante cambios de control. */
const PREVIEW_DEBOUNCE_MS = 300

/** Encabezado de sección: mismo tratamiento que los títulos de columna (uppercase muted). */
function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-[0.8rem] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
      {children}
    </h3>
  )
}

/** Icono "?" que revela la explicación del control en un tooltip. */
function HelpHint({ children }: { children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label="Ayuda"
          className="relative inline-flex size-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring after:absolute after:-inset-2"
        >
          <CircleHelp className="size-3.5" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs text-pretty">
        {children}
      </TooltipContent>
    </Tooltip>
  )
}

/** Botón que restaura el valor predeterminado del control. */
function ResetButton({ onClick }: { onClick: () => void }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label="Restablecer valor predeterminado"
          onClick={onClick}
          className="relative inline-flex size-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring after:absolute after:-inset-2"
        >
          <RotateCcw className="size-3.5" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top">Restablecer</TooltipContent>
    </Tooltip>
  )
}

interface SliderFieldProps {
  label: string
  value: number
  defaultValue: number
  min: number
  max: number
  step: number
  disabled?: boolean
  help?: ReactNode
  format?: (value: number) => string
  onChange: (value: number) => void
  className?: string
}

/** Slider con label, readout numérico a la derecha, ayuda y reset a default. */
function SliderField({
  label,
  value,
  defaultValue,
  min,
  max,
  step,
  disabled,
  help,
  format,
  onChange,
  className
}: SliderFieldProps) {
  const isDirty = value !== defaultValue

  return (
    <Field className={className}>
      <div className="flex w-full items-center gap-1">
        <FieldLabel>{label}</FieldLabel>
        {help ? <HelpHint>{help}</HelpHint> : null}
        <span className="ml-auto shrink-0 text-sm tabular-nums text-muted-foreground">
          {format ? format(value) : value}
        </span>
        {isDirty && !disabled ? <ResetButton onClick={() => onChange(defaultValue)} /> : null}
      </div>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(v) => onChange(v[0] ?? value)}
        disabled={disabled}
      />
    </Field>
  )
}

/** Los 10 controles del Gradio original, reagrupados por flujo de trabajo. */
function Controls({ disabled }: { disabled: boolean }) {
  const params = useHalftoneStore((state) => state.params)
  const setParam = useHalftoneStore((state) => state.setParam)
  const resetParam = useHalftoneStore((state) => state.resetParam)

  const tramDisabled = disabled || params.method === 'diffusion'
  const cropDisabled = disabled || !params.cropBlackBackground

  const set = <K extends keyof HalftoneParams>(key: K) => (value: HalftoneParams[K]) =>
    setParam(key, value)

  return (
    <div className="flex flex-col gap-6">
      {/* --- Preparación --- */}
      <section className="flex flex-col gap-3">
        <SectionHeading>Preparación</SectionHeading>
        <Field orientation="horizontal">
          <Checkbox
            id="halftone-crop-black"
            checked={params.cropBlackBackground}
            onCheckedChange={(value) => set('cropBlackBackground')(value === true)}
            disabled={disabled}
          />
          <div className="flex flex-1 flex-col gap-0.5">
            <FieldLabel htmlFor="halftone-crop-black">Recortar fondo negro</FieldLabel>
            <FieldDescription>
              Elimina automáticamente los bordes casi-negros alrededor de la imagen (útil para
              imágenes generadas por IA con relleno oscuro).
            </FieldDescription>
          </div>
          {params.cropBlackBackground !== DEFAULT_PARAMS.cropBlackBackground && !disabled ? (
            <ResetButton onClick={() => resetParam('cropBlackBackground')} />
          ) : null}
        </Field>
        <SliderField
          label="Umbral de recorte"
          value={params.cropBlackThreshold}
          defaultValue={DEFAULT_PARAMS.cropBlackThreshold}
          min={0}
          max={255}
          step={1}
          disabled={cropDisabled}
          help="Los píxeles cuyos canales RGB están todos por debajo de este valor se tratan como fondo negro. Más alto = recorte más agresivo."
          onChange={set('cropBlackThreshold')}
          className="pl-5"
        />
      </section>

      {/* --- Tonalidad --- */}
      <section className="flex flex-col gap-3">
        <SectionHeading>Tonalidad</SectionHeading>
        <SliderField
          label="Punto negro"
          value={params.blackPoint}
          defaultValue={DEFAULT_PARAMS.blackPoint}
          min={0}
          max={255}
          step={1}
          disabled={disabled}
          help="Las sombras más oscuras que este valor se vuelven negro puro (transparente). Súbelo para profundizar sombras y quitar ruido tenue."
          onChange={set('blackPoint')}
        />
        <SliderField
          label="Gamma"
          value={params.gamma}
          defaultValue={DEFAULT_PARAMS.gamma}
          min={0.1}
          max={3.0}
          step={0.1}
          disabled={disabled}
          format={(value) => value.toFixed(1)}
          help="Controla el brillo de los medios tonos. Menor que 1 = medios más oscuros, mayor que 1 = medios más claros. Funciona como el deslizador central de Niveles en Photoshop."
          onChange={set('gamma')}
        />
        <SliderField
          label="Punto blanco"
          value={params.whitePoint}
          defaultValue={DEFAULT_PARAMS.whitePoint}
          min={0}
          max={255}
          step={1}
          disabled={disabled}
          help="Los brillos más claros que este valor se vuelven blanco puro (totalmente opaco). Bájalo para aclarar la imagen en general."
          onChange={set('whitePoint')}
        />
      </section>

      {/* --- Semitonos --- */}
      <section className="flex flex-col gap-3">
        <SectionHeading>Semitonos</SectionHeading>
        <Field>
          <div className="flex w-full items-center gap-1">
            <FieldLabel>Método</FieldLabel>
            <HelpHint>
              «Trama» usa un patrón clásico de puntos. «Difusión» usa difusión de error
              Floyd–Steinberg para una textura más orgánica, tipo grano.
            </HelpHint>
            {params.method !== DEFAULT_PARAMS.method && !disabled ? (
              <ResetButton onClick={() => resetParam('method')} />
            ) : null}
          </div>
          <ToggleGroup
            type="single"
            variant="outline"
            spacing={0}
            className="w-full"
            value={params.method}
            onValueChange={(value) => {
              if (value) set('method')(value as HalftoneMethod)
            }}
            disabled={disabled}
            aria-label="Método de semitonos"
          >
            <ToggleGroupItem value="halftone" className="flex-1">
              Trama (halftone)
            </ToggleGroupItem>
            <ToggleGroupItem value="diffusion" className="flex-1">
              Difusión
            </ToggleGroupItem>
          </ToggleGroup>
        </Field>
        <FieldDescription>
          La frecuencia, el ángulo y la forma del punto solo aplican al método «Trama».
        </FieldDescription>
        <SliderField
          label="Frecuencia de trama (LPI)"
          value={params.screenFrequency}
          defaultValue={DEFAULT_PARAMS.screenFrequency}
          min={5}
          max={100}
          step={1}
          disabled={tramDisabled}
          help="Líneas por pulgada — controla la densidad del punto. Más bajo = puntos más grandes y visibles. 25–45 es típico para estampado de prendas."
          onChange={set('screenFrequency')}
        />
        <SliderField
          label="Ángulo de trama (°)"
          value={params.screenAngle}
          defaultValue={DEFAULT_PARAMS.screenAngle}
          min={0}
          max={90}
          step={0.5}
          disabled={tramDisabled}
          format={(value) => value.toFixed(1)}
          help="Rotación de la grilla de puntos. 22.5° o 45° son elecciones comunes para evitar muaré."
          onChange={set('screenAngle')}
        />
        <Field>
          <div className="flex w-full items-center gap-1">
            <FieldLabel>Forma del punto</FieldLabel>
            <HelpHint>
              «Redondo» produce puntos circulares clásicos. «Línea» produce tramado de líneas
              paralelas (aspecto de grabado).
            </HelpHint>
            {params.dotShape !== DEFAULT_PARAMS.dotShape && !tramDisabled ? (
              <ResetButton onClick={() => resetParam('dotShape')} />
            ) : null}
          </div>
          <ToggleGroup
            type="single"
            variant="outline"
            spacing={0}
            className="w-full"
            value={params.dotShape}
            onValueChange={(value) => {
              if (value) set('dotShape')(value as DotShape)
            }}
            disabled={tramDisabled}
            aria-label="Forma del punto"
          >
            <ToggleGroupItem value="round" className="flex-1">
              Redondo
            </ToggleGroupItem>
            <ToggleGroupItem value="line" className="flex-1">
              Línea
            </ToggleGroupItem>
          </ToggleGroup>
        </Field>
      </section>

      {/* --- Salida --- */}
      <section className="flex flex-col gap-3">
        <SectionHeading>Salida</SectionHeading>
        <Field orientation="horizontal">
          <Checkbox
            id="halftone-invert-dark"
            checked={params.invertForDarkShirt}
            onCheckedChange={(value) => set('invertForDarkShirt')(value === true)}
            disabled={disabled}
          />
          <div className="flex flex-1 flex-col gap-0.5">
            <FieldLabel htmlFor="halftone-invert-dark">Invertir para prenda oscura</FieldLabel>
            <FieldDescription>
              Invierte los valores tonales para que el diseño imprima correctamente sobre tela
              oscura (tinta clara sobre fondo oscuro).
            </FieldDescription>
          </div>
          {params.invertForDarkShirt !== DEFAULT_PARAMS.invertForDarkShirt && !disabled ? (
            <ResetButton onClick={() => resetParam('invertForDarkShirt')} />
          ) : null}
        </Field>
      </section>
    </div>
  )
}

export function HalftonePanel() {
  const params = useHalftoneStore((state) => state.params)
  const inputPath = useHalftoneStore((state) => state.inputPath)
  const inputPreview = useHalftoneStore((state) => state.inputPreview)
  const previewSrc = useHalftoneStore((state) => state.previewSrc)
  const isPreviewing = useHalftoneStore((state) => state.isPreviewing)
  const isSaving = useHalftoneStore((state) => state.isSaving)
  const savedPath = useHalftoneStore((state) => state.savedPath)
  const error = useHalftoneStore((state) => state.error)

  const setInputSource = useHalftoneStore((state) => state.setInputSource)
  const setError = useHalftoneStore((state) => state.setError)
  const refreshPreview = useHalftoneStore((state) => state.refreshPreview)
  const saveFullRes = useHalftoneStore((state) => state.saveFullRes)

  // Preview en vivo: se regenera (con debounce) ante cualquier cambio de parámetro o imagen.
  useEffect(() => {
    if (!inputPath) return
    const handle = setTimeout(() => void refreshPreview(), PREVIEW_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [inputPath, params, refreshPreview])

  const canSave = Boolean(inputPath) && !isSaving

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {error ? (
        <p className="error flex-none" role="alert">
          {error}
        </p>
      ) : null}

      <div className="columns columns--scale min-h-0 flex-1">
        <section className="column panel">
          <h2 className="column__title">Imagen de entrada</h2>
          <ImageInputZone
            path={inputPath}
            previewUrl={inputPreview}
            onSource={setInputSource}
            onError={setError}
            disabled={isSaving}
            tabId="halftone"
            selectLabel="Seleccionar imagen"
            selectIcon={FileImage}
            alt="Imagen de entrada para semitonos"
            emptyLabel="Selecciona, pega (Ctrl+V) o arrastra una imagen (JPEG, PNG o WEBP)"
          />
        </section>

        <section className="column panel panel--form overflow-y-auto">
          <h2 className="column__title">Ajustes</h2>
          <Controls disabled={false} />
        </section>

        <section className="column panel">
          <h2 className="column__title">
            Previsualización
            {isPreviewing ? (
              <Loader2 className="ml-2 inline size-4 animate-spin align-[-2px]" />
            ) : null}
          </h2>
          <ImageViewer
            src={previewSrc}
            alt="Previsualización del halftone"
            emptyLabel="La previsualización aparecerá aquí"
          />

          <div className="flex items-stretch gap-3">
            <Alert className="flex-1">
              <Info />
              <AlertTitle>Se exporta a resolución completa</AlertTitle>
              <AlertDescription>
                La previsualización es de baja resolución y solo orientativa. Al guardar se
                genera el render definitivo a 4500×5400 @300; el método «Difusión» puede diferir
                levemente de la previsualización.
              </AlertDescription>
            </Alert>
            <AppButton
              type="button"
              icon={isSaving ? Loader2 : Download}
              iconClassName={isSaving ? 'animate-spin' : undefined}
              onClick={() => void saveFullRes()}
              disabled={!canSave}
              className="self-center"
            >
              {isSaving ? 'Generando…' : 'Guardar'}
            </AppButton>
          </div>
          {savedPath ? <p className="path-hint">Guardado en: {savedPath}</p> : null}
        </section>
      </div>
    </div>
  )
}
