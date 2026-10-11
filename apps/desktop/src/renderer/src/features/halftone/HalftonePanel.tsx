import { useEffect, type ReactNode } from 'react'
import {
  CircleHelp,
  Download,
  FileImage,
  Info,
  Loader2,
  RotateCcw,
  TriangleAlert
} from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

import { AppButton } from '../../core/components/AppButton'
import { ImageInputZone } from '../../core/imaging/ImageInputZone'
import { ImageResultView } from '../../core/imaging/ImageResultView'
import {
  DEFAULT_COMMON,
  useHalftoneStore,
  type BackgroundMode,
  type DetectedBackground,
  type DotShape,
  type Garment,
  type HalftoneAdvanced,
  type HalftoneMethod,
  type HalftoneMode
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

const GARMENT_LABEL: Record<Garment, string> = { dark: 'Oscura', light: 'Clara' }

const BACKGROUND_LABEL: Record<DetectedBackground, string> = {
  transparent: 'Transparente',
  black: 'Negro',
  white: 'Blanco',
  none: 'Sin fondo uniforme'
}

/** Píxeles @300 DPI → centímetros con un decimal. */
function toCm(px: number): string {
  return ((px / 300) * 2.54).toFixed(1)
}

/** Prenda y fondo: aplican en ambos modos. */
function CommonControls({ disabled }: { disabled: boolean }) {
  const common = useHalftoneStore((state) => state.common)
  const setCommon = useHalftoneStore((state) => state.setCommon)
  const detected = useHalftoneStore((state) => state.analysis?.detectedBackground ?? null)

  const effectiveBackground = common.background === 'auto' ? detected : common.background
  const usesThreshold = effectiveBackground === 'black' || effectiveBackground === 'white'

  return (
    <section className="flex flex-col gap-3">
      <SectionHeading>Prenda y fondo</SectionHeading>
      <Field>
        <div className="flex w-full items-center gap-1">
          <FieldLabel>Color de la prenda</FieldLabel>
          <HelpHint>
            En prenda oscura se imprime tinta en las zonas claras del diseño y las oscuras dejan
            ver la tela. En prenda clara es al revés.
          </HelpHint>
        </div>
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          className="w-full"
          value={common.garment}
          onValueChange={(value) => {
            if (value) setCommon('garment', value as Garment)
          }}
          disabled={disabled}
          aria-label="Color de la prenda"
        >
          <ToggleGroupItem value="dark" className="flex-1">
            {GARMENT_LABEL.dark}
          </ToggleGroupItem>
          <ToggleGroupItem value="light" className="flex-1">
            {GARMENT_LABEL.light}
          </ToggleGroupItem>
        </ToggleGroup>
      </Field>
      <Field>
        <div className="flex w-full items-center gap-1">
          <FieldLabel htmlFor="halftone-background">Fondo de la imagen</FieldLabel>
          <HelpHint>
            El fondo nunca recibe tinta y la imagen se recorta al diseño. En «Automático» se
            detecta: transparencia real, o un borde mayoritariamente negro o blanco. Los
            negros/blancos interiores del diseño se conservan.
          </HelpHint>
        </div>
        <Select
          value={common.background}
          onValueChange={(value) => setCommon('background', value as BackgroundMode)}
          disabled={disabled}
        >
          <SelectTrigger id="halftone-background" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value="auto">
                Automático{detected ? ` (${BACKGROUND_LABEL[detected].toLowerCase()})` : ''}
              </SelectItem>
              <SelectItem value="transparent">{BACKGROUND_LABEL.transparent}</SelectItem>
              <SelectItem value="black">{BACKGROUND_LABEL.black}</SelectItem>
              <SelectItem value="white">{BACKGROUND_LABEL.white}</SelectItem>
              <SelectItem value="none">Ninguno (tramar todo)</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>
      </Field>
      {usesThreshold ? (
        <SliderField
          label="Tolerancia del fondo"
          value={common.backgroundThreshold}
          defaultValue={DEFAULT_COMMON.backgroundThreshold}
          min={0}
          max={128}
          step={1}
          disabled={disabled}
          help="Cuánto puede alejarse un píxel del negro/blanco puro para contar como fondo. Súbelo si queda un halo alrededor del diseño; bájalo si se come partes del diseño."
          onChange={(value) => setCommon('backgroundThreshold', value)}
          className="pl-5"
        />
      ) : null}
    </section>
  )
}

/** Resumen de solo lectura de lo que eligió el modo rápido. */
function QuickSummary() {
  const analysis = useHalftoneStore((state) => state.analysis)
  const isPreviewing = useHalftoneStore((state) => state.isPreviewing)
  const resolved = analysis?.resolved

  return (
    <section className="flex flex-col gap-3">
      <SectionHeading>Ajustes automáticos</SectionHeading>
      {resolved ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          <dt className="text-muted-foreground">Niveles</dt>
          <dd className="tabular-nums">
            {resolved.blackPoint} – {resolved.whitePoint}
          </dd>
          <dt className="text-muted-foreground">Trama</dt>
          <dd className="tabular-nums">
            Redonda · {resolved.screenFrequency} LPI · {resolved.screenAngle.toFixed(1)}°
          </dd>
          <dt className="text-muted-foreground">Punto mínimo</dt>
          <dd className="tabular-nums">{Math.round((resolved.minDotTone / 255) * 100)} %</dd>
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">
          {isPreviewing ? 'Analizando la imagen…' : 'Carga una imagen para analizarla.'}
        </p>
      )}
      <FieldDescription>
        Niveles según el rango tonal del diseño, trama redonda segura para DTF y sin puntos más
        pequeños de los que el film puede sujetar. Pasa a «Avanzado» para ajustarlos: partirás
        de estos valores.
      </FieldDescription>
    </section>
  )
}

/** Controles del modo avanzado (los del Space + punto mínimo). */
function AdvancedControls({ disabled }: { disabled: boolean }) {
  const params = useHalftoneStore((state) => state.advanced)
  const baseline = useHalftoneStore((state) => state.advancedBaseline)
  const setAdvanced = useHalftoneStore((state) => state.setAdvanced)
  const resetAdvanced = useHalftoneStore((state) => state.resetAdvanced)

  const tramDisabled = disabled || params.method === 'diffusion'

  const set = <K extends keyof HalftoneAdvanced>(key: K) => (value: HalftoneAdvanced[K]) =>
    setAdvanced(key, value)

  return (
    <>
      {/* --- Tonalidad --- */}
      <section className="flex flex-col gap-3">
        <SectionHeading>Tonalidad</SectionHeading>
        <SliderField
          label="Punto negro"
          value={params.blackPoint}
          defaultValue={baseline.blackPoint}
          min={0}
          max={255}
          step={1}
          disabled={disabled}
          help="Las sombras más oscuras que este valor se vuelven negro puro. Súbelo para profundizar sombras y quitar ruido tenue."
          onChange={set('blackPoint')}
        />
        <SliderField
          label="Gamma"
          value={params.gamma}
          defaultValue={baseline.gamma}
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
          defaultValue={baseline.whitePoint}
          min={0}
          max={255}
          step={1}
          disabled={disabled}
          help="Los brillos más claros que este valor se vuelven blanco puro. Bájalo para aclarar la imagen en general."
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
              Floyd–Steinberg para una textura más orgánica, tipo grano (puntos de 1 px que
              pueden no adherir en DTF).
            </HelpHint>
            {params.method !== baseline.method && !disabled ? (
              <ResetButton onClick={() => resetAdvanced('method')} />
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
          La frecuencia, el ángulo, la forma y el punto mínimo solo aplican al método «Trama».
        </FieldDescription>
        <SliderField
          label="Frecuencia de trama (LPI)"
          value={params.screenFrequency}
          defaultValue={baseline.screenFrequency}
          min={5}
          max={100}
          step={1}
          disabled={tramDisabled}
          help="Densidad del punto. Más bajo = puntos más grandes y visibles. Esta trama pone dos puntos por ciclo, así que se ve más fina que el mismo LPI en otros programas: 20–30 equivale a lo típico de DTF."
          onChange={set('screenFrequency')}
        />
        <SliderField
          label="Ángulo de trama (°)"
          value={params.screenAngle}
          defaultValue={baseline.screenAngle}
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
            {params.dotShape !== baseline.dotShape && !tramDisabled ? (
              <ResetButton onClick={() => resetAdvanced('dotShape')} />
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
        <SliderField
          label="Punto mínimo"
          value={params.minDotTone}
          defaultValue={baseline.minDotTone}
          min={0}
          max={100}
          step={1}
          disabled={tramDisabled}
          format={(value) => `${Math.round((value / 255) * 100)} %`}
          help="Los tonos más claros que este porcentaje quedan sin tinta y los más oscuros que su opuesto, sólidos: así no se generan puntos ni huecos diminutos que el film no sujeta. 0 = sin límite (comportamiento original)."
          onChange={set('minDotTone')}
        />
      </section>
    </>
  )
}

function Controls({ disabled }: { disabled: boolean }) {
  const mode = useHalftoneStore((state) => state.mode)
  const setMode = useHalftoneStore((state) => state.setMode)

  return (
    <div className="flex flex-col gap-6">
      <ToggleGroup
        type="single"
        variant="outline"
        spacing={0}
        className="w-full"
        value={mode}
        onValueChange={(value) => {
          if (value) setMode(value as HalftoneMode)
        }}
        disabled={disabled}
        aria-label="Modo"
      >
        <ToggleGroupItem value="quick" className="flex-1">
          Rápido
        </ToggleGroupItem>
        <ToggleGroupItem value="advanced" className="flex-1">
          Avanzado
        </ToggleGroupItem>
      </ToggleGroup>

      <CommonControls disabled={disabled} />
      {mode === 'quick' ? <QuickSummary /> : <AdvancedControls disabled={disabled} />}
    </div>
  )
}

export function HalftonePanel() {
  const mode = useHalftoneStore((state) => state.mode)
  const common = useHalftoneStore((state) => state.common)
  const advanced = useHalftoneStore((state) => state.advanced)
  const analysis = useHalftoneStore((state) => state.analysis)
  const inputPath = useHalftoneStore((state) => state.inputPath)
  const inputPreview = useHalftoneStore((state) => state.inputPreview)
  const previewSrc = useHalftoneStore((state) => state.previewSrc)
  const isPreviewing = useHalftoneStore((state) => state.isPreviewing)
  const isSaving = useHalftoneStore((state) => state.isSaving)
  const savedPath = useHalftoneStore((state) => state.savedPath)
  const outputPath = useHalftoneStore((state) => state.outputPath)
  const outputUrl = useHalftoneStore((state) => state.outputUrl)
  const error = useHalftoneStore((state) => state.error)

  const setInputSource = useHalftoneStore((state) => state.setInputSource)
  const setError = useHalftoneStore((state) => state.setError)
  const refreshPreview = useHalftoneStore((state) => state.refreshPreview)
  const saveFullRes = useHalftoneStore((state) => state.saveFullRes)

  // Preview en vivo: se regenera (con debounce) ante cualquier cambio de parámetro o imagen.
  // En modo rápido los controles avanzados no influyen en el resultado.
  const advancedDeps = mode === 'advanced' ? advanced : null
  useEffect(() => {
    if (!inputPath) return
    const handle = setTimeout(() => void refreshPreview(), PREVIEW_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [inputPath, mode, common, advancedDeps, refreshPreview])

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
          <ImageResultView
            src={outputUrl ?? previewSrc}
            alt="Previsualización del halftone"
            emptyLabel="La previsualización aparecerá aquí"
            sourcePath={outputPath}
            sendTargets={['mockups']}
          />

          {analysis && analysis.warnings.length > 0 ? (
            <Alert>
              <TriangleAlert />
              <AlertTitle>Revisa antes de imprimir</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-4">
                  {analysis.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="flex items-stretch gap-3">
            <Alert className="flex-1">
              <Info />
              <AlertTitle>Se exporta a resolución completa</AlertTitle>
              <AlertDescription>
                {analysis
                  ? `Al guardar se genera el render definitivo a ${analysis.outputWidth}×${analysis.outputHeight} px @300 DPI (${toCm(analysis.outputWidth)}×${toCm(analysis.outputHeight)} cm), recortado al diseño.`
                  : 'Al guardar se genera el render definitivo @300 DPI, recortado al diseño.'}{' '}
                La previsualización es de baja resolución y solo orientativa; el método «Difusión»
                puede diferir levemente.
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
