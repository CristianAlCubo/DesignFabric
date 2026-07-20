import { useEffect } from 'react'

import { Button } from '@/components/ui/button'

import { TransparentImage } from '../../core/components/TransparentImage'
import { StrategyList } from './StrategyList'
import { useRemoveBackgroundStore } from './store'

export function RemoveBackgroundPanel() {
  const strategies = useRemoveBackgroundStore((state) => state.strategies)
  const selectedStrategyId = useRemoveBackgroundStore((state) => state.selectedStrategyId)
  const inputPath = useRemoveBackgroundStore((state) => state.inputPath)
  const inputPreview = useRemoveBackgroundStore((state) => state.inputPreview)
  const outputPreview = useRemoveBackgroundStore((state) => state.outputPreview)
  const outputDurationSeconds = useRemoveBackgroundStore((state) => state.durationSeconds)
  const error = useRemoveBackgroundStore((state) => state.error)
  const isProcessing = useRemoveBackgroundStore((state) => state.isProcessing)
  const isExporting = useRemoveBackgroundStore((state) => state.isExporting)

  const loadStrategies = useRemoveBackgroundStore((state) => state.loadStrategies)
  const setSelectedStrategyId = useRemoveBackgroundStore((state) => state.setSelectedStrategyId)
  const selectInputImage = useRemoveBackgroundStore((state) => state.selectInputImage)
  const processRemoval = useRemoveBackgroundStore((state) => state.processRemoval)
  const exportOutput = useRemoveBackgroundStore((state) => state.exportOutput)
  const sendToScale = useRemoveBackgroundStore((state) => state.sendToScale)

  useEffect(() => {
    void loadStrategies()
  }, [loadStrategies])

  const canProcess = Boolean(inputPath && selectedStrategyId) && !isProcessing

  return (
    <div className="columns" role="tabpanel" id="panel-remove" aria-labelledby="tab-remove">
      <section className="column panel">
        <h2 className="column__title">Entrada</h2>
        <Button
          type="button"
          variant="outline"
          onClick={() => void selectInputImage()}
          disabled={isProcessing}
        >
          Seleccionar imagen
        </Button>
        {inputPath ? <p className="path-hint">{inputPath}</p> : null}
        <TransparentImage
          src={inputPreview}
          alt="Imagen de entrada"
          emptyLabel="Selecciona una imagen PNG, JPG o WEBP"
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
        <Button
          type="button"
          onClick={() => void processRemoval()}
          disabled={!canProcess}
        >
          {isProcessing ? 'Procesando…' : 'Procesar'}
        </Button>
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
      </section>

      <section className="column panel">
        <h2 className="column__title">Resultado</h2>
        <TransparentImage
          src={outputPreview}
          alt="Imagen procesada"
          emptyLabel="El PNG con transparencia aparecerá aquí"
          durationSeconds={outputDurationSeconds}
          actions={
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => void exportOutput()}
                disabled={isExporting}
              >
                {isExporting ? 'Exportando…' : 'Exportar'}
              </Button>
              <Button type="button" variant="outline" onClick={sendToScale}>
                Enviar a escalado
              </Button>
            </>
          }
        />
      </section>
    </div>
  )
}
