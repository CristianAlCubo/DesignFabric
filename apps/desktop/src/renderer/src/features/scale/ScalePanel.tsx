import { useEffect } from 'react'

import { Button } from '@/components/ui/button'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
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

import { TransparentImage } from '../../core/components/TransparentImage'
import type { ScaleFactor, SizeInputMode } from './store'
import { useScaleStore } from './store'
import { StrategyList } from './StrategyList'

const SIZE_MODE_OPTIONS: { id: SizeInputMode; label: string }[] = [
  { id: 'factor', label: 'Factor' },
  { id: 'manual', label: 'Manual' }
]

const FACTOR_OPTIONS: ScaleFactor[] = [2, 4]

export function ScalePanel() {
  const defaults = useScaleStore((state) => state.scaleDefaults)
  const scaleStrategies = useScaleStore((state) => state.scaleStrategies)
  const selectedScaleStrategyId = useScaleStore((state) => state.selectedScaleStrategyId)
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
  const isExporting = useScaleStore((state) => state.isExporting)
  const showAdvanced = useScaleStore((state) => state.showAdvanced)
  const sizeInputMode = useScaleStore((state) => state.sizeInputMode)
  const scaleFactor = useScaleStore((state) => state.scaleFactor)
  const width = useScaleStore((state) => state.width)
  const height = useScaleStore((state) => state.height)
  const dpi = useScaleStore((state) => state.dpi)
  const cornerThreshold = useScaleStore((state) => state.cornerThreshold)
  const colorPrecision = useScaleStore((state) => state.colorPrecision)
  const filterSpeckle = useScaleStore((state) => state.filterSpeckle)
  const layerDifference = useScaleStore((state) => state.layerDifference)
  const colormode = useScaleStore((state) => state.colormode)
  const mode = useScaleStore((state) => state.mode)

  const loadScaleDefaults = useScaleStore((state) => state.loadScaleDefaults)
  const loadScaleStrategies = useScaleStore((state) => state.loadScaleStrategies)
  const setSelectedScaleStrategyId = useScaleStore((state) => state.setSelectedScaleStrategyId)
  const selectInputImage = useScaleStore((state) => state.selectInputImage)
  const runScale = useScaleStore((state) => state.runScale)
  const exportOutput = useScaleStore((state) => state.exportOutput)
  const setShowAdvanced = useScaleStore((state) => state.setShowAdvanced)
  const setSizeInputMode = useScaleStore((state) => state.setSizeInputMode)
  const setScaleFactor = useScaleStore((state) => state.setScaleFactor)
  const setWidth = useScaleStore((state) => state.setWidth)
  const setHeight = useScaleStore((state) => state.setHeight)
  const setDpi = useScaleStore((state) => state.setDpi)
  const setCornerThreshold = useScaleStore((state) => state.setCornerThreshold)
  const setColorPrecision = useScaleStore((state) => state.setColorPrecision)
  const setFilterSpeckle = useScaleStore((state) => state.setFilterSpeckle)
  const setLayerDifference = useScaleStore((state) => state.setLayerDifference)
  const setColormode = useScaleStore((state) => state.setColormode)
  const setMode = useScaleStore((state) => state.setMode)

  useEffect(() => {
    void loadScaleStrategies()
    void loadScaleDefaults()
  }, [loadScaleStrategies, loadScaleDefaults])

  const canScale = Boolean(inputPath && selectedScaleStrategyId) && !isScaling
  const showVectorKnobs = selectedScaleStrategyId === 'vector'
  const targetWidth =
    inputWidth !== null && sizeInputMode === 'factor' ? inputWidth * scaleFactor : null
  const targetHeight =
    inputHeight !== null && sizeInputMode === 'factor' ? inputHeight * scaleFactor : null

  return (
    <div className="columns columns--scale" role="tabpanel" id="panel-scale" aria-labelledby="tab-scale">
      <section className="column panel">
        <h2 className="column__title">Entrada PNG</h2>
        <Button
          type="button"
          variant="outline"
          onClick={() => void selectInputImage()}
          disabled={isScaling}
        >
          Seleccionar PNG
        </Button>
        {inputPath ? <p className="path-hint">{inputPath}</p> : null}
        <TransparentImage
          src={inputPreview}
          alt="PNG de entrada para escalado"
          emptyLabel="Selecciona un PNG recortado (por ejemplo, el resultado de eliminación de fondo)"
        />
      </section>

      <section className="column panel panel--form">
        <h2 className="column__title">Estrategia</h2>
        <StrategyList
          strategies={scaleStrategies}
          selectedId={selectedScaleStrategyId}
          onSelect={(id) => {
            if (id === 'vector' || id === 'realesrgan') {
              setSelectedScaleStrategyId(id)
            }
          }}
          disabled={isScaling}
          name="scale-strategy"
          legend="Estrategia de escalado"
        />

        <h2 className="column__title">Resolución</h2>

        <ToggleGroup
          type="single"
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
            <ToggleGroupItem key={option.id} value={option.id}>
              {option.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>

        {sizeInputMode === 'factor' ? (
          <>
            <ToggleGroup
              type="single"
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
                <ToggleGroupItem key={factor} value={String(factor)}>
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

        <Field>
          <FieldLabel htmlFor="scale-dpi">DPI</FieldLabel>
          <Input
            id="scale-dpi"
            type="number"
            min={1}
            step={1}
            value={dpi}
            onChange={(event) => setDpi(event.target.value)}
            disabled={isScaling}
          />
        </Field>
        <p className="muted field-hint">
          DPI de rasterización
          {defaults ? ` (default: ${defaults.dpi}).` : '.'}
        </p>

        {showVectorKnobs ? (
          <>
            <h2 className="column__title">Calidad del trazado</h2>
            <Field>
              <FieldLabel>Corner threshold ({cornerThreshold})</FieldLabel>
              <Slider
                min={0}
                max={180}
                value={[cornerThreshold]}
                onValueChange={(vals) => setCornerThreshold(vals[0])}
                disabled={isScaling}
              />
            </Field>
            <Field>
              <FieldLabel>Color precision ({colorPrecision})</FieldLabel>
              <Slider
                min={1}
                max={8}
                value={[colorPrecision]}
                onValueChange={(vals) => setColorPrecision(vals[0])}
                disabled={isScaling}
              />
            </Field>

            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowAdvanced(!showAdvanced)}
              disabled={isScaling}
            >
              {showAdvanced ? 'Ocultar avanzado' : 'Mostrar avanzado'}
            </Button>

            {showAdvanced ? (
              <div className="advanced-fields">
                <Field>
                  <FieldLabel>Filter speckle ({filterSpeckle})</FieldLabel>
                  <Slider
                    min={0}
                    max={20}
                    value={[filterSpeckle]}
                    onValueChange={(vals) => setFilterSpeckle(vals[0])}
                    disabled={isScaling}
                  />
                </Field>
                <Field>
                  <FieldLabel>Layer difference ({layerDifference})</FieldLabel>
                  <Slider
                    min={1}
                    max={64}
                    value={[layerDifference]}
                    onValueChange={(vals) => setLayerDifference(vals[0])}
                    disabled={isScaling}
                  />
                </Field>
                <Field>
                  <FieldLabel>Color mode</FieldLabel>
                  <Select
                    value={colormode}
                    onValueChange={(value) =>
                      setColormode(value === 'binary' ? 'binary' : 'color')
                    }
                    disabled={isScaling}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value="color">color</SelectItem>
                        <SelectItem value="binary">binary</SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </Field>
                <Field>
                  <FieldLabel>Mode</FieldLabel>
                  <Select
                    value={mode}
                    onValueChange={(value) => {
                      if (value === 'polygon' || value === 'none' || value === 'spline') {
                        setMode(value)
                      }
                    }}
                    disabled={isScaling}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem value="spline">spline</SelectItem>
                        <SelectItem value="polygon">polygon</SelectItem>
                        <SelectItem value="none">none</SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </Field>
              </div>
            ) : null}
          </>
        ) : null}

        <Button type="button" onClick={() => void runScale()} disabled={!canScale}>
          {isScaling ? 'Escalando…' : 'Escalar'}
        </Button>
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
        <TransparentImage
          src={outputPreview}
          alt="PNG escalado"
          emptyLabel="El PNG a alta resolución aparecerá aquí"
          durationSeconds={outputDurationSeconds}
          actions={
            <Button
              type="button"
              variant="outline"
              onClick={() => void exportOutput()}
              disabled={isExporting}
            >
              {isExporting ? 'Exportando…' : 'Exportar'}
            </Button>
          }
        />
        {outputPath ? <p className="path-hint">{outputPath}</p> : null}
      </section>
    </div>
  )
}
