import { useEffect } from 'react'
import { FileImage, Scaling } from 'lucide-react'

import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import { ImageInputZone } from '../../core/imaging/ImageInputZone'
import { ImageResultView } from '../../core/imaging/ImageResultView'
import type { ScaleFactor, SizeInputMode } from './store'
import { useScaleStore } from './store'

const SIZE_MODE_OPTIONS: { id: SizeInputMode; label: string }[] = [
  { id: 'factor', label: 'Factor' },
  { id: 'manual', label: 'Manual' }
]

const FACTOR_OPTIONS: ScaleFactor[] = [2, 4]

export function ScalePanel() {
  const inputPath = useScaleStore((state) => state.inputPath)
  const inputPreview = useScaleStore((state) => state.inputPreview)
  const inputWidth = useScaleStore((state) => state.inputWidth)
  const inputHeight = useScaleStore((state) => state.inputHeight)
  const outputPath = useScaleStore((state) => state.outputPath)
  const outputPreview = useScaleStore((state) => state.outputPreview)
  const outputDurationSeconds = useScaleStore((state) => state.durationSeconds)
  const error = useScaleStore((state) => state.error)
  const warning = useScaleStore((state) => state.warning)
  const isScaling = useScaleStore((state) => state.isScaling)
  const sizeInputMode = useScaleStore((state) => state.sizeInputMode)
  const scaleFactor = useScaleStore((state) => state.scaleFactor)
  const width = useScaleStore((state) => state.width)
  const height = useScaleStore((state) => state.height)

  const loadScaleDefaults = useScaleStore((state) => state.loadScaleDefaults)
  const setInputSource = useScaleStore((state) => state.setInputSource)
  const setError = useScaleStore((state) => state.setError)
  const runScale = useScaleStore((state) => state.runScale)
  const setSizeInputMode = useScaleStore((state) => state.setSizeInputMode)
  const setScaleFactor = useScaleStore((state) => state.setScaleFactor)
  const setWidth = useScaleStore((state) => state.setWidth)
  const setHeight = useScaleStore((state) => state.setHeight)

  useEffect(() => {
    void loadScaleDefaults()
  }, [loadScaleDefaults])

  const canScale = Boolean(inputPath) && !isScaling
  const targetWidth =
    inputWidth !== null && sizeInputMode === 'factor' ? inputWidth * scaleFactor : null
  const targetHeight =
    inputHeight !== null && sizeInputMode === 'factor' ? inputHeight * scaleFactor : null

  return (
    <div className="columns columns--scale">
      <section className="column panel">
        <h2 className="column__title">Entrada PNG</h2>
        <ImageInputZone
          path={inputPath}
          previewUrl={inputPreview}
          onSource={setInputSource}
          onError={setError}
          disabled={isScaling}
          tabId="scale"
          selectLabel="Seleccionar PNG"
          selectIcon={FileImage}
          alt="PNG de entrada para escalado"
          emptyLabel="Selecciona, pega (Ctrl+V) o arrastra un PNG recortado (p. ej. el resultado de eliminación de fondo)"
        />
      </section>

      <section className="column panel panel--form">
        <h2 className="column__title">Resolución</h2>

        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          className="w-full"
          value={sizeInputMode}
          onValueChange={(value) => {
            if (value === 'factor' || value === 'manual') {
              setSizeInputMode(value)
            }
          }}
          disabled={isScaling}
          aria-label="Modo de tamaño"
        >
          {SIZE_MODE_OPTIONS.map((option) => (
            <ToggleGroupItem key={option.id} value={option.id} className="flex-1">
              {option.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>

        {sizeInputMode === 'factor' ? (
          <>
            <ToggleGroup
              type="single"
              variant="outline"
              spacing={0}
              className="w-full"
              value={String(scaleFactor)}
              onValueChange={(value) => {
                if (value === '2' || value === '4') {
                  setScaleFactor(Number(value) as ScaleFactor)
                }
              }}
              disabled={isScaling}
              aria-label="Factor de escala"
            >
              {FACTOR_OPTIONS.map((factor) => (
                <ToggleGroupItem key={factor} value={String(factor)} className="flex-1">
                  {factor}x
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            <p className="muted field-hint">
              {targetWidth !== null && targetHeight !== null
                ? `Tamaño final: ${targetWidth} × ${targetHeight}`
                : 'Carga una imagen para ver el tamaño final.'}
            </p>
          </>
        ) : (
          <>
            <Field>
              <FieldLabel htmlFor="scale-width">Ancho (px)</FieldLabel>
              <Input
                id="scale-width"
                type="number"
                min={1}
                placeholder="Requerido"
                value={width}
                onChange={(event) => setWidth(event.target.value)}
                disabled={isScaling}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="scale-height">Alto (px)</FieldLabel>
              <Input
                id="scale-height"
                type="number"
                min={1}
                placeholder="Requerido"
                value={height}
                onChange={(event) => setHeight(event.target.value)}
                disabled={isScaling}
              />
            </Field>
            <p className="muted field-hint">Indica al menos ancho o alto en píxeles.</p>
          </>
        )}

        <AppButton type="button" icon={Scaling} onClick={() => void runScale()} disabled={!canScale}>
          {isScaling ? 'Escalando…' : 'Escalar'}
        </AppButton>
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
        {warning ? (
          <p className="warning" role="status">
            {warning}
          </p>
        ) : null}
      </section>

      <section className="column panel">
        <h2 className="column__title">Resultado</h2>
        <ImageResultView
          src={outputPreview}
          alt="PNG escalado"
          emptyLabel="El PNG a alta resolución aparecerá aquí"
          durationSeconds={outputDurationSeconds}
          exportName="escalado.png"
          onExportError={setError}
          sourcePath={outputPath}
          sendTargets={['halftone', 'image-convert']}
        />
        {outputPath ? <p className="path-hint">{outputPath}</p> : null}
      </section>
    </div>
  )
}
