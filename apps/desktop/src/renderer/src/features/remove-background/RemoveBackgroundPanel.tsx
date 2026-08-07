import { useEffect } from 'react'
import { Eraser } from 'lucide-react'

import { AppButton } from '../../core/components/AppButton'
import { ImageInputZone } from '../../core/imaging/ImageInputZone'
import { ImageResultView } from '../../core/imaging/ImageResultView'
import { StrategyList } from './StrategyList'
import { useRemoveBackgroundStore } from './store'

export function RemoveBackgroundPanel() {
  const strategies = useRemoveBackgroundStore((state) => state.strategies)
  const selectedStrategyId = useRemoveBackgroundStore((state) => state.selectedStrategyId)
  const inputPath = useRemoveBackgroundStore((state) => state.inputPath)
  const inputPreview = useRemoveBackgroundStore((state) => state.inputPreview)
  const outputPath = useRemoveBackgroundStore((state) => state.outputPath)
  const outputPreview = useRemoveBackgroundStore((state) => state.outputPreview)
  const outputDurationSeconds = useRemoveBackgroundStore((state) => state.durationSeconds)
  const error = useRemoveBackgroundStore((state) => state.error)
  const isProcessing = useRemoveBackgroundStore((state) => state.isProcessing)

  const loadStrategies = useRemoveBackgroundStore((state) => state.loadStrategies)
  const setSelectedStrategyId = useRemoveBackgroundStore((state) => state.setSelectedStrategyId)
  const setInputSource = useRemoveBackgroundStore((state) => state.setInputSource)
  const setError = useRemoveBackgroundStore((state) => state.setError)
  const processRemoval = useRemoveBackgroundStore((state) => state.processRemoval)

  useEffect(() => {
    void loadStrategies()
  }, [loadStrategies])

  const canProcess = Boolean(inputPath && selectedStrategyId) && !isProcessing

  return (
    <div className="columns">
      <section className="column panel">
        <h2 className="column__title">Entrada</h2>
        <ImageInputZone
          path={inputPath}
          previewUrl={inputPreview}
          onSource={setInputSource}
          onError={setError}
          disabled={isProcessing}
          tabId="remove-background"
          alt="Imagen de entrada"
          emptyLabel="Selecciona, pega (Ctrl+V) o arrastra una imagen PNG, JPG o WEBP"
        />
      </section>

      <section className="column panel panel--form">
        <h2 className="column__title">Estrategia</h2>
        <StrategyList
          strategies={strategies}
          selectedId={selectedStrategyId}
          onSelect={setSelectedStrategyId}
          disabled={isProcessing}
        />
        <AppButton
          type="button"
          icon={Eraser}
          onClick={() => void processRemoval()}
          disabled={!canProcess}
        >
          {isProcessing ? 'Procesando…' : 'Procesar'}
        </AppButton>
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
      </section>

      <section className="column panel">
        <h2 className="column__title">Resultado</h2>
        <ImageResultView
          src={outputPreview}
          alt="Imagen procesada"
          emptyLabel="El PNG con transparencia aparecerá aquí"
          durationSeconds={outputDurationSeconds}
          exportName="sin-fondo.png"
          onExportError={setError}
          sourcePath={outputPath}
          sendTargets={['scale', 'halftone', 'image-convert']}
        />
      </section>
    </div>
  )
}
