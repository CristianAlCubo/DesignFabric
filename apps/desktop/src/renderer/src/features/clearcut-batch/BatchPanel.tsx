import { Files, Folder, FolderOutput } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import { useJobProgress } from '../../core/hooks/useJobProgress'
import { useStickyBatchProgress, useProgressAnchor } from './batchProgress'
import { BatchJobStrip } from './BatchJobStrip'
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

interface PathPickerProps {
  icon: typeof Folder
  label: string
  meta?: string | null
  title?: string
  empty: boolean
  disabled?: boolean
  onClick: () => void
}

/** Control de ruta de altura fija: la selección vive en la etiqueta, sin bloques extra. */
function PathPicker({ icon, label, meta, title, empty, disabled, onClick }: PathPickerProps) {
  return (
    <AppButton
      type="button"
      variant="outline"
      icon={icon}
      className={`batch-path-picker${empty ? ' batch-path-picker--empty' : ''}`}
      disabled={disabled}
      title={title}
      onClick={onClick}
    >
      <span className="batch-path-picker__label">{label}</span>
      {meta ? <span className="batch-path-picker__meta tabular-nums">{meta}</span> : null}
    </AppButton>
  )
}

export function BatchPanel() {
  const strategies = useBatchStore((state) => state.strategies)
  const batchInputMode = useBatchStore((state) => state.batchInputMode)
  const batchInputDir = useBatchStore((state) => state.batchInputDir)
  const batchInputFiles = useBatchStore((state) => state.batchInputFiles)
  const batchInputCount = useBatchStore((state) => state.batchInputCount)
  const batchOutputDir = useBatchStore((state) => state.batchOutputDir)
  const batchRemovalStrategyId = useBatchStore((state) => state.batchRemovalStrategyId)
  const batchFactor = useBatchStore((state) => state.batchFactor)
  const batchReport = useBatchStore((state) => state.batchReport)
  const batchError = useBatchStore((state) => state.batchError)
  const isBatchRunning = useBatchStore((state) => state.isBatchRunning)
  const batchPhase = useBatchStore((state) => state.batchPhase)
  const jobId = useBatchStore((state) => state.jobId)

  const loadStrategies = useBatchStore((state) => state.loadStrategies)
  const setBatchInputMode = useBatchStore((state) => state.setBatchInputMode)
  const setBatchRemovalStrategyId = useBatchStore((state) => state.setBatchRemovalStrategyId)
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
  const finalizedRef = useRef(false)

  const { events, latestEvent } = useJobProgress(jobId)
  const progress = useStickyBatchProgress(events)
  const lastCompletedAt = useProgressAnchor(progress)

  useEffect(() => {
    void loadStrategies()
  }, [loadStrategies])

  useEffect(() => {
    if (!isBatchRunning) return
    const id = window.setInterval(() => setNow(performance.now()), 500)
    return () => window.clearInterval(id)
  }, [isBatchRunning])

  useEffect(() => {
    if (jobId) {
      setStartedAt(performance.now())
      finalizedRef.current = false
    }
  }, [jobId])

  useEffect(() => {
    if (!latestEvent || !jobId) return

    if (
      (latestEvent.type === 'completed' || latestEvent.type === 'failed') &&
      !finalizedRef.current
    ) {
      finalizedRef.current = true
      void finalizeJob()
    }
  }, [latestEvent, jobId, finalizeJob])

  const hasInput =
    batchInputMode === 'folder' ? Boolean(batchInputDir) : batchInputFiles.length > 0

  const runBlockers = useMemo(() => {
    const blockers: string[] = []
    if (!hasInput) blockers.push('Selecciona una carpeta o archivos de entrada')
    if (batchInputCount === 0) blockers.push('La entrada no contiene imágenes compatibles')
    if (!batchOutputDir.trim()) blockers.push('Elige una carpeta de salida')
    if (!batchRemovalStrategyId) blockers.push('Elige una estrategia de recorte')
    return blockers
  }, [hasInput, batchInputCount, batchOutputDir, batchRemovalStrategyId])

  const canRun = runBlockers.length === 0 && !isBatchRunning

  const removalLabel =
    strategies.find((item) => item.id === batchRemovalStrategyId)?.label ?? '—'

  const inputEmpty =
    batchInputMode === 'folder' ? !batchInputDir : batchInputFiles.length === 0
  const inputLabel =
    batchInputMode === 'folder'
      ? batchInputDir
        ? basename(batchInputDir)
        : 'Seleccionar carpeta'
      : batchInputFiles.length > 0
        ? batchInputFiles.length === 1
          ? basename(batchInputFiles[0])
          : `${batchInputFiles.length} archivos`
        : 'Seleccionar archivos'
  const inputMeta =
    batchInputMode === 'folder' && batchInputDir && batchInputCount !== null
      ? `${batchInputCount} img`
      : null
  const inputTitle =
    batchInputMode === 'folder'
      ? batchInputDir ?? undefined
      : batchInputFiles.length > 0
        ? batchInputFiles.map(basename).slice(0, 8).join('\n') +
          (batchInputFiles.length > 8 ? `\n… y ${batchInputFiles.length - 8} más` : '')
        : undefined

  const outputEmpty = !batchOutputDir.trim()
  const outputLabel = outputEmpty ? 'Elegir carpeta de salida' : basename(batchOutputDir)

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

        <PathPicker
          icon={batchInputMode === 'folder' ? Folder : Files}
          label={inputLabel}
          meta={inputMeta}
          title={inputTitle}
          empty={inputEmpty}
          disabled={isBatchRunning}
          onClick={() =>
            void (batchInputMode === 'folder' ? selectBatchFolder() : selectBatchFiles())
          }
        />

        <h2 className="column__title">Salida</h2>
        <PathPicker
          icon={FolderOutput}
          label={outputLabel}
          title={outputEmpty ? undefined : batchOutputDir}
          empty={outputEmpty}
          disabled={isBatchRunning}
          onClick={() => void selectBatchOutputDir()}
        />

        <details className="batch-setup-details" open={!isBatchRunning && !batchReport}>
          <summary className="column__title batch-setup-details__summary">
            Recorte y escalado
          </summary>
          <div className="batch-setup-details__body">
            {(isBatchRunning || batchReport) && (
              <p className="batch-setup-summary muted">
                {removalLabel} · Real-ESRGAN · {batchFactor}x
              </p>
            )}
            <h2 className="column__title">Recorte</h2>
            <StrategyList
              strategies={strategies}
              selectedId={batchRemovalStrategyId}
              onSelect={setBatchRemovalStrategyId}
              disabled={isBatchRunning}
              name="batch-removal-strategy"
              legend="Estrategia de recorte"
            />

            <h2 className="column__title">Factor de escalado</h2>
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
          </div>
        </details>

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
          lastCompletedAt={lastCompletedAt}
          canRun={canRun}
          runBlockers={runBlockers}
          isRunning={isBatchRunning}
          inputCount={batchInputCount}
          now={now}
          onRun={() => void runBatch()}
          onCancel={() => void cancelBatch()}
        />
        <BatchQueue
          items={batchReport?.items ?? []}
          report={batchReport}
          outputDir={batchOutputDir || null}
          isRunning={isBatchRunning}
          progressEvents={events}
          onOpenOutput={() => void openBatchOutputDir()}
        />
      </div>
    </div>
  )
}
