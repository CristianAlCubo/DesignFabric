import { Files, Folder, FolderOutput } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import { useJobProgress } from '../../core/hooks/useJobProgress'
import { BatchJobStrip, type BatchProgressDisplay } from './BatchJobStrip'
import { BatchQueue } from './BatchQueue'
import type { BatchInputMode, ScaleFactor } from './store'
import { useBatchStore } from './store'
import { StrategyList } from './StrategyList'

const INPUT_MODE_OPTIONS: { id: BatchInputMode; label: string; icon: typeof Folder }[] = [
  { id: 'folder', label: 'Carpeta', icon: Folder },
  { id: 'files', label: 'Archivos', icon: Files }
]

const FACTOR_OPTIONS: ScaleFactor[] = [2, 4]

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

export function BatchPanel() {
  const strategies = useBatchStore((state) => state.strategies)
  const scaleStrategies = useBatchStore((state) => state.scaleStrategies)
  const batchInputMode = useBatchStore((state) => state.batchInputMode)
  const batchInputDir = useBatchStore((state) => state.batchInputDir)
  const batchInputFiles = useBatchStore((state) => state.batchInputFiles)
  const batchOutputDir = useBatchStore((state) => state.batchOutputDir)
  const batchRemovalStrategyId = useBatchStore((state) => state.batchRemovalStrategyId)
  const batchScaleStrategyId = useBatchStore((state) => state.batchScaleStrategyId)
  const batchFactor = useBatchStore((state) => state.batchFactor)
  const batchReport = useBatchStore((state) => state.batchReport)
  const batchError = useBatchStore((state) => state.batchError)
  const isBatchRunning = useBatchStore((state) => state.isBatchRunning)
  const batchPhase = useBatchStore((state) => state.batchPhase)
  const jobId = useBatchStore((state) => state.jobId)

  const loadStrategies = useBatchStore((state) => state.loadStrategies)
  const loadScaleStrategies = useBatchStore((state) => state.loadScaleStrategies)
  const setBatchInputMode = useBatchStore((state) => state.setBatchInputMode)
  const setBatchRemovalStrategyId = useBatchStore((state) => state.setBatchRemovalStrategyId)
  const setBatchScaleStrategyId = useBatchStore((state) => state.setBatchScaleStrategyId)
  const setBatchFactor = useBatchStore((state) => state.setBatchFactor)
  const selectBatchOutputDir = useBatchStore((state) => state.selectBatchOutputDir)
  const selectBatchFolder = useBatchStore((state) => state.selectBatchFolder)
  const selectBatchFiles = useBatchStore((state) => state.selectBatchFiles)
  const runBatch = useBatchStore((state) => state.runBatch)
  const cancelBatch = useBatchStore((state) => state.cancelBatch)
  const finalizeJob = useBatchStore((state) => state.finalizeJob)
  const openBatchOutputDir = useBatchStore((state) => state.openBatchOutputDir)

  const [now, setNow] = useState(() => performance.now())
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [itemCompletedAt, setItemCompletedAt] = useState<number[]>([])
  const finalizedRef = useRef(false)

  const { latestEvent } = useJobProgress(jobId)

  useEffect(() => {
    void loadStrategies()
    void loadScaleStrategies()
  }, [loadStrategies, loadScaleStrategies])

  useEffect(() => {
    if (!isBatchRunning) return
    const id = window.setInterval(() => setNow(performance.now()), 500)
    return () => window.clearInterval(id)
  }, [isBatchRunning])

  // Reinicia el cronómetro local cuando arranca un nuevo job.
  useEffect(() => {
    if (jobId) {
      setStartedAt(performance.now())
      setItemCompletedAt([])
      finalizedRef.current = false
    }
  }, [jobId])

  // Traduce los eventos de progreso (WS) del job activo a marcas de tiempo
  // por ítem, y detecta el fin del job para pedir el reporte final por HTTP.
  useEffect(() => {
    if (!latestEvent || !jobId) return

    if (latestEvent.type === 'progress') {
      setItemCompletedAt((previous) => [...previous, performance.now()])
    }

    if (
      (latestEvent.type === 'completed' || latestEvent.type === 'failed') &&
      !finalizedRef.current
    ) {
      finalizedRef.current = true
      void finalizeJob()
    }
  }, [latestEvent, jobId, finalizeJob])

  const progress: BatchProgressDisplay | null =
    latestEvent && latestEvent.current !== null && latestEvent.total !== null
      ? {
          current: latestEvent.current,
          total: latestEvent.total,
          path: latestEvent.detail ?? latestEvent.message ?? ''
        }
      : null

  const hasInput =
    batchInputMode === 'folder' ? Boolean(batchInputDir) : batchInputFiles.length > 0
  const canRun =
    hasInput &&
    batchOutputDir.trim().length > 0 &&
    Boolean(batchRemovalStrategyId) &&
    Boolean(batchScaleStrategyId) &&
    !isBatchRunning

  return (
    <div className="batch-layout" role="tabpanel" id="panel-batch" aria-labelledby="tab-batch">
      <aside className="batch-setup panel panel--form">
        <h2 className="column__title">Entrada</h2>

        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          value={batchInputMode}
          onValueChange={(value) => {
            if (value === 'folder' || value === 'files') {
              setBatchInputMode(value)
            }
          }}
          disabled={isBatchRunning}
          aria-label="Estrategia de entrada"
          className="w-full"
        >
          {INPUT_MODE_OPTIONS.map((option) => {
            const Icon = option.icon
            return (
              <ToggleGroupItem key={option.id} value={option.id} className="flex-1">
                <Icon data-icon="inline-start" aria-hidden />
                {option.label}
              </ToggleGroupItem>
            )
          })}
        </ToggleGroup>

        {batchInputMode === 'folder' ? (
          <>
            <AppButton
              type="button"
              variant="outline"
              icon={Folder}
              onClick={() => void selectBatchFolder()}
              disabled={isBatchRunning}
            >
              Seleccionar carpeta
            </AppButton>
            {batchInputDir ? (
              <p className="path-hint" title={batchInputDir}>
                {batchInputDir}
              </p>
            ) : null}
            <p className="muted field-hint">Imágenes compatibles de la carpeta (sin subcarpetas).</p>
          </>
        ) : (
          <>
            <AppButton
              type="button"
              variant="outline"
              icon={Files}
              onClick={() => void selectBatchFiles()}
              disabled={isBatchRunning}
            >
              Seleccionar archivos
            </AppButton>
            {batchInputFiles.length > 0 ? (
              <ul className="batch-file-list">
                {batchInputFiles.map((filePath) => (
                  <li key={filePath} className="path-hint" title={filePath}>
                    {basename(filePath)}
                  </li>
                ))}
              </ul>
            ) : null}
            <p className="muted field-hint">Solo se procesarán los archivos seleccionados.</p>
          </>
        )}

        <h2 className="column__title">Salida</h2>
        <AppButton
          type="button"
          variant="outline"
          icon={FolderOutput}
          onClick={() => void selectBatchOutputDir()}
          disabled={isBatchRunning}
        >
          Elegir carpeta de salida
        </AppButton>
        {batchOutputDir ? (
          <p className="path-hint" title={batchOutputDir}>
            {batchOutputDir}
          </p>
        ) : null}

        <h2 className="column__title">Recorte</h2>
        <StrategyList
          strategies={strategies}
          selectedId={batchRemovalStrategyId}
          onSelect={setBatchRemovalStrategyId}
          disabled={isBatchRunning}
          name="batch-removal-strategy"
          legend="Estrategia de recorte"
        />

        <h2 className="column__title">Escalado</h2>
        <StrategyList
          strategies={scaleStrategies}
          selectedId={batchScaleStrategyId}
          onSelect={(id) => {
            if (id === 'vector' || id === 'realesrgan') {
              setBatchScaleStrategyId(id)
            }
          }}
          disabled={isBatchRunning}
          name="batch-scale-strategy"
          legend="Estrategia de escalado"
        />

        <h2 className="column__title">Factor</h2>
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          value={String(batchFactor)}
          onValueChange={(value) => {
            if (value === '2' || value === '4') {
              setBatchFactor(Number(value) as ScaleFactor)
            }
          }}
          disabled={isBatchRunning}
          aria-label="Factor de escala"
          className="w-full"
        >
          {FACTOR_OPTIONS.map((factor) => (
            <ToggleGroupItem key={factor} value={String(factor)} className="flex-1">
              {factor}x
            </ToggleGroupItem>
          ))}
        </ToggleGroup>

        {batchError ? (
          <p className="error" role="alert">
            {batchError}
          </p>
        ) : null}
      </aside>

      <div className="batch-stage">
        <BatchJobStrip
          phase={batchPhase}
          progress={progress}
          startedAt={startedAt}
          itemCompletedAt={itemCompletedAt}
          canRun={canRun}
          isRunning={isBatchRunning}
          now={now}
          onRun={() => void runBatch()}
          onCancel={() => void cancelBatch()}
        />
        {/*
          Limitación conocida de esta fase: el backend solo expone la lista
          detallada de ítems (`items`) en el resultado final del job
          (`GET /api/jobs/{id}`), no por evento WS individual. Por eso la
          cola de ítems permanece vacía mientras el lote corre y se llena de
          una sola vez al terminar, aunque la barra de progreso y el archivo
          actual sí se actualizan en vivo vía `useJobProgress`.
        */}
        <BatchQueue
          items={batchReport?.items ?? []}
          report={batchReport}
          outputDir={batchOutputDir || null}
          onOpenOutput={() => void openBatchOutputDir()}
        />
      </div>
    </div>
  )
}
