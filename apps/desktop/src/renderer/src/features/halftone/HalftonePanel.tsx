import { useEffect } from 'react'
import { Download, FileImage, Info, Loader2 } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldLabel } from '@/components/ui/field'
import { Slider } from '@/components/ui/slider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import { TransparentImage } from '../../core/components/TransparentImage'
import {
  useHalftoneStore,
  type DotShape,
  type HalftoneMethod,
  type HalftoneParams
} from './store'

/** Debounce (ms) del preview en vivo ante cambios de control. */
const PREVIEW_DEBOUNCE_MS = 300

/** Controles que replican 1:1 el panel del Gradio original, con sus tooltips traducidos. */
function Controls({ disabled }: { disabled: boolean }) {
  const params = useHalftoneStore((state) => state.params)
  const setParam = useHalftoneStore((state) => state.setParam)

  const tramDisabled = disabled || params.method === 'diffusion'

  const set = <K extends keyof HalftoneParams>(key: K) => (value: HalftoneParams[K]) =>
    setParam(key, value)

  return (
    <div className="flex flex-col gap-5">
      {/* --- Recorte --- */}
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold">Recorte</h3>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={params.cropBlackBackground}
            onCheckedChange={(value) => set('cropBlackBackground')(value === true)}
            disabled={disabled}
          />
          Recortar fondo negro
        </label>
        <p className="muted field-hint">
          Elimina automáticamente los bordes casi-negros alrededor de la imagen (útil para
          imágenes generadas por IA con relleno oscuro).
        </p>
        <Field>
          <FieldLabel>Umbral de recorte: {params.cropBlackThreshold}</FieldLabel>
          <Slider
            min={0}
            max={255}
            step={1}
            value={[params.cropBlackThreshold]}
            onValueChange={(v) => set('cropBlackThreshold')(v[0] ?? params.cropBlackThreshold)}
            disabled={disabled || !params.cropBlackBackground}
          />
          <p className="muted field-hint">
            Los píxeles cuyos canales RGB están todos por debajo de este valor se tratan como
            fondo negro. Más alto = recorte más agresivo.
          </p>
        </Field>
      </div>

      {/* --- Curva tonal (Niveles) --- */}
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold">Curva tonal (Niveles)</h3>
        <Field>
          <FieldLabel>Punto negro: {params.blackPoint}</FieldLabel>
          <Slider
            min={0}
            max={255}
            step={1}
            value={[params.blackPoint]}
            onValueChange={(v) => set('blackPoint')(v[0] ?? params.blackPoint)}
            disabled={disabled}
          />
          <p className="muted field-hint">
            Las sombras más oscuras que este valor se vuelven negro puro (transparente). Súbelo
            para profundizar sombras y quitar ruido tenue.
          </p>
        </Field>
        <Field>
          <FieldLabel>Punto blanco: {params.whitePoint}</FieldLabel>
          <Slider
            min={0}
            max={255}
            step={1}
            value={[params.whitePoint]}
            onValueChange={(v) => set('whitePoint')(v[0] ?? params.whitePoint)}
            disabled={disabled}
          />
          <p className="muted field-hint">
            Los brillos más claros que este valor se vuelven blanco puro (totalmente opaco).
            Bájalo para aclarar la imagen en general.
          </p>
        </Field>
        <Field>
          <FieldLabel>Gamma: {params.gamma.toFixed(1)}</FieldLabel>
          <Slider
            min={0.1}
            max={3.0}
            step={0.1}
            value={[params.gamma]}
            onValueChange={(v) => set('gamma')(v[0] ?? params.gamma)}
            disabled={disabled}
          />
          <p className="muted field-hint">
            Controla el brillo de los medios tonos. &lt;1 = medios más oscuros, &gt;1 = medios
            más claros. Funciona como el deslizador central de Niveles en Photoshop.
          </p>
        </Field>
      </div>

      {/* --- Modo de salida --- */}
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold">Modo de salida</h3>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={params.invertForDarkShirt}
            onCheckedChange={(value) => set('invertForDarkShirt')(value === true)}
            disabled={disabled}
          />
          Invertir para prenda oscura
        </label>
        <p className="muted field-hint">
          Invierte los valores tonales para que el diseño imprima correctamente sobre tela
          oscura (tinta clara sobre fondo oscuro).
        </p>
      </div>

      {/* --- Semitonos --- */}
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold">Semitonos</h3>
        <Field>
          <FieldLabel>Método</FieldLabel>
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
          <p className="muted field-hint">
            «Trama» usa un patrón clásico de puntos. «Difusión» usa difusión de error
            Floyd–Steinberg para una textura más orgánica, tipo grano.
          </p>
        </Field>

        <Field>
          <FieldLabel>Frecuencia de trama (LPI): {params.screenFrequency}</FieldLabel>
          <Slider
            min={5}
            max={100}
            step={1}
            value={[params.screenFrequency]}
            onValueChange={(v) => set('screenFrequency')(v[0] ?? params.screenFrequency)}
            disabled={tramDisabled}
          />
          <p className="muted field-hint">
            Líneas por pulgada — controla la densidad del punto. Más bajo = puntos más grandes y
            visibles. 25–45 es típico para estampado de prendas. Solo aplica al método «Trama».
          </p>
        </Field>

        <Field>
          <FieldLabel>Ángulo de trama (°): {params.screenAngle.toFixed(1)}</FieldLabel>
          <Slider
            min={0}
            max={90}
            step={0.5}
            value={[params.screenAngle]}
            onValueChange={(v) => set('screenAngle')(v[0] ?? params.screenAngle)}
            disabled={tramDisabled}
          />
          <p className="muted field-hint">
            Rotación de la grilla de puntos. 22.5° o 45° son elecciones comunes para evitar
            muaré. Solo aplica al método «Trama».
          </p>
        </Field>

        <Field>
          <FieldLabel>Forma del punto</FieldLabel>
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
          <p className="muted field-hint">
            «Redondo» produce puntos circulares clásicos. «Línea» produce tramado de líneas
            paralelas (aspecto de grabado). Solo aplica al método «Trama».
          </p>
        </Field>
      </div>
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

  const selectInputImage = useHalftoneStore((state) => state.selectInputImage)
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
          <AppButton
            type="button"
            variant="outline"
            icon={FileImage}
            onClick={() => void selectInputImage()}
            disabled={isSaving}
          >
            Seleccionar imagen
          </AppButton>
          {inputPath ? <p className="path-hint">{inputPath}</p> : null}
          <TransparentImage
            src={inputPreview}
            alt="Imagen de entrada para semitonos"
            emptyLabel="Selecciona una imagen (JPEG, PNG o WEBP)"
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
          <TransparentImage
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
