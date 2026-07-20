import { useEffect } from 'react'

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
        <button
          type="button"
          className="btn"
          onClick={() => void selectInputImage()}
          disabled={isScaling}
        >
          Seleccionar PNG
        </button>
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

        <div className="segmented" role="group" aria-label="Modo de tamaño">
          {SIZE_MODE_OPTIONS.map((option) => {
            const selected = sizeInputMode === option.id
            return (
              <button
                key={option.id}
                type="button"
                className={selected ? 'segmented__btn segmented__btn--active' : 'segmented__btn'}
                aria-pressed={selected}
                onClick={() => setSizeInputMode(option.id)}
                disabled={isScaling}
              >
                {option.label}
              </button>
            )
          })}
        </div>

        {sizeInputMode === 'factor' ? (
          <>
            <div className="segmented" role="group" aria-label="Factor de escala">
              {FACTOR_OPTIONS.map((factor) => {
                const selected = scaleFactor === factor
                return (
                  <button
                    key={factor}
                    type="button"
                    className={selected ? 'segmented__btn segmented__btn--active' : 'segmented__btn'}
                    aria-pressed={selected}
                    onClick={() => setScaleFactor(factor)}
                    disabled={isScaling}
                  >
                    {factor}x
                  </button>
                )
              })}
            </div>
            <p className="muted field-hint">
              {targetWidth !== null && targetHeight !== null
                ? `Tamaño final: ${targetWidth} × ${targetHeight}`
                : 'Carga una imagen para ver el tamaño final.'}
            </p>
          </>
        ) : (
          <>
            <label className="field">
              <span className="field__label">Ancho (px)</span>
              <input
                className="field__input"
                type="number"
                min={1}
                placeholder="Requerido"
                value={width}
                onChange={(event) => setWidth(event.target.value)}
                disabled={isScaling}
              />
            </label>
            <label className="field">
              <span className="field__label">Alto (px)</span>
              <input
                className="field__input"
                type="number"
                min={1}
                placeholder="Requerido"
                value={height}
                onChange={(event) => setHeight(event.target.value)}
                disabled={isScaling}
              />
            </label>
            <p className="muted field-hint">Indica al menos ancho o alto en píxeles.</p>
          </>
        )}

        <label className="field">
          <span className="field__label">DPI</span>
          <input
            className="field__input"
            type="number"
            min={1}
            step={1}
            value={dpi}
            onChange={(event) => setDpi(event.target.value)}
            disabled={isScaling}
          />
        </label>
        <p className="muted field-hint">
          DPI de rasterización
          {defaults ? ` (default: ${defaults.dpi}).` : '.'}
        </p>

        {showVectorKnobs ? (
          <>
            <h2 className="column__title">Calidad del trazado</h2>
            <label className="field">
              <span className="field__label">Corner threshold ({cornerThreshold})</span>
              <input
                className="field__range"
                type="range"
                min={0}
                max={180}
                value={cornerThreshold}
                onChange={(event) => setCornerThreshold(Number(event.target.value))}
                disabled={isScaling}
              />
            </label>
            <label className="field">
              <span className="field__label">Color precision ({colorPrecision})</span>
              <input
                className="field__range"
                type="range"
                min={1}
                max={8}
                value={colorPrecision}
                onChange={(event) => setColorPrecision(Number(event.target.value))}
                disabled={isScaling}
              />
            </label>

            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setShowAdvanced(!showAdvanced)}
              disabled={isScaling}
            >
              {showAdvanced ? 'Ocultar avanzado' : 'Mostrar avanzado'}
            </button>

            {showAdvanced ? (
              <div className="advanced-fields">
                <label className="field">
                  <span className="field__label">Filter speckle ({filterSpeckle})</span>
                  <input
                    className="field__range"
                    type="range"
                    min={0}
                    max={20}
                    value={filterSpeckle}
                    onChange={(event) => setFilterSpeckle(Number(event.target.value))}
                    disabled={isScaling}
                  />
                </label>
                <label className="field">
                  <span className="field__label">Layer difference ({layerDifference})</span>
                  <input
                    className="field__range"
                    type="range"
                    min={1}
                    max={64}
                    value={layerDifference}
                    onChange={(event) => setLayerDifference(Number(event.target.value))}
                    disabled={isScaling}
                  />
                </label>
                <label className="field">
                  <span className="field__label">Color mode</span>
                  <select
                    className="field__input"
                    value={colormode}
                    onChange={(event) =>
                      setColormode(event.target.value === 'binary' ? 'binary' : 'color')
                    }
                    disabled={isScaling}
                  >
                    <option value="color">color</option>
                    <option value="binary">binary</option>
                  </select>
                </label>
                <label className="field">
                  <span className="field__label">Mode</span>
                  <select
                    className="field__input"
                    value={mode}
                    onChange={(event) => {
                      const value = event.target.value
                      if (value === 'polygon' || value === 'none' || value === 'spline') {
                        setMode(value)
                      }
                    }}
                    disabled={isScaling}
                  >
                    <option value="spline">spline</option>
                    <option value="polygon">polygon</option>
                    <option value="none">none</option>
                  </select>
                </label>
              </div>
            ) : null}
          </>
        ) : null}

        <button
          type="button"
          className="btn btn--primary"
          onClick={() => void runScale()}
          disabled={!canScale}
        >
          {isScaling ? 'Escalando…' : 'Escalar'}
        </button>
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
            <button
              type="button"
              className="btn"
              onClick={() => void exportOutput()}
              disabled={isExporting}
            >
              {isExporting ? 'Exportando…' : 'Exportar'}
            </button>
          }
        />
        {outputPath ? <p className="path-hint">{outputPath}</p> : null}
      </section>
    </div>
  )
}
