import { useEffect, useMemo } from 'react'
import { Download, FileImage, ImagePlus, Loader2, RefreshCw, X } from 'lucide-react'

import { Checkbox } from '@/components/ui/checkbox'
import { Field, FieldLabel } from '@/components/ui/field'
import { Slider } from '@/components/ui/slider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import { ProgressBar } from '../../core/components/ProgressBar'
import { TransparentImage } from '../../core/components/TransparentImage'
import { useJobProgress } from '../../core/hooks/useJobProgress'
import {
  basename,
  formatSupportsQuality,
  TARGET_FORMATS,
  useImageConvertStore,
  type ConvertMode,
  type TargetFormat
} from './store'

const MODE_OPTIONS: { id: ConvertMode; label: string }[] = [
  { id: 'single', label: 'Individual' },
  { id: 'batch', label: 'Lote' }
]

/** Controles de formato/calidad compartidos por ambos modos. */
function FormatOptions({ disabled }: { disabled: boolean }) {
  const targetFormat = useImageConvertStore((state) => state.targetFormat)
  const quality = useImageConvertStore((state) => state.quality)
  const webpLossless = useImageConvertStore((state) => state.webpLossless)
  const setTargetFormat = useImageConvertStore((state) => state.setTargetFormat)
  const setQuality = useImageConvertStore((state) => state.setQuality)
  const setWebpLossless = useImageConvertStore((state) => state.setWebpLossless)

  const qualityEnabled =
    formatSupportsQuality(targetFormat) && !(targetFormat === 'WEBP' && webpLossless)

  return (
    <div className="flex flex-col gap-4">
      <Field>
        <FieldLabel>Formato destino</FieldLabel>
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          className="w-full"
          value={targetFormat}
          onValueChange={(value) => {
            if (value) setTargetFormat(value as TargetFormat)
          }}
          disabled={disabled}
          aria-label="Formato destino"
        >
          {TARGET_FORMATS.map((format) => (
            <ToggleGroupItem key={format} value={format} className="flex-1">
              {format}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </Field>

      {targetFormat === 'WEBP' ? (
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={webpLossless}
            onCheckedChange={(value) => setWebpLossless(value === true)}
            disabled={disabled}
          />
          WEBP sin pérdida (lossless)
        </label>
      ) : null}

      <Field>
        <FieldLabel>Calidad: {qualityEnabled ? quality : '—'}</FieldLabel>
        <Slider
          min={0}
          max={100}
          step={1}
          value={[quality]}
          onValueChange={(values) => setQuality(values[0] ?? quality)}
          disabled={disabled || !qualityEnabled}
          aria-label="Calidad de compresión"
        />
        <p className="muted field-hint">
          {formatSupportsQuality(targetFormat)
            ? 'Aplica a JPEG y WEBP con pérdida.'
            : 'PNG se guarda optimizado, sin control de calidad.'}
        </p>
      </Field>
    </div>
  )
}

function SingleMode() {
  const inputPath = useImageConvertStore((state) => state.inputPath)
  const inputPreview = useImageConvertStore((state) => state.inputPreview)
  const outputPath = useImageConvertStore((state) => state.outputPath)
  const outputPreview = useImageConvertStore((state) => state.outputPreview)
  const isConverting = useImageConvertStore((state) => state.isConverting)
  const isExporting = useImageConvertStore((state) => state.isExporting)

  const selectInputImage = useImageConvertStore((state) => state.selectInputImage)
  const runConvert = useImageConvertStore((state) => state.runConvert)
  const exportOutput = useImageConvertStore((state) => state.exportOutput)

  const canConvert = Boolean(inputPath) && !isConverting

  return (
    <div className="columns columns--scale">
      <section className="column panel">
        <h2 className="column__title">Imagen de entrada</h2>
        <AppButton
          type="button"
          variant="outline"
          icon={FileImage}
          onClick={() => void selectInputImage()}
          disabled={isConverting}
        >
          Seleccionar imagen
        </AppButton>
        {inputPath ? <p className="path-hint">{inputPath}</p> : null}
        <TransparentImage
          src={inputPreview}
          alt="Imagen de entrada para conversión"
          emptyLabel="Selecciona una imagen (JPEG, PNG o WEBP)"
        />
      </section>

      <section className="column panel panel--form">
        <h2 className="column__title">Formato</h2>
        <FormatOptions disabled={isConverting} />
        <AppButton
          type="button"
          icon={isConverting ? Loader2 : RefreshCw}
          iconClassName={isConverting ? 'animate-spin' : undefined}
          onClick={() => void runConvert()}
          disabled={!canConvert}
        >
          {isConverting ? 'Convirtiendo…' : 'Convertir'}
        </AppButton>
      </section>

      <section className="column panel">
        <h2 className="column__title">Resultado</h2>
        <TransparentImage
          src={outputPreview}
          alt="Imagen convertida"
          emptyLabel="La imagen convertida aparecerá aquí"
          actions={
            <AppButton
              type="button"
              variant="outline"
              icon={Download}
              onClick={() => void exportOutput()}
              disabled={isExporting}
            >
              {isExporting ? 'Exportando…' : 'Exportar'}
            </AppButton>
          }
        />
        {outputPath ? <p className="path-hint">{outputPath}</p> : null}
      </section>
    </div>
  )
}

function BatchMode() {
  const images = useImageConvertStore((state) => state.images)
  const jobId = useImageConvertStore((state) => state.jobId)
  const batchResult = useImageConvertStore((state) => state.batchResult)
  const isRunning = useImageConvertStore((state) => state.isRunning)

  const selectImages = useImageConvertStore((state) => state.selectImages)
  const removeImage = useImageConvertStore((state) => state.removeImage)
  const runBatch = useImageConvertStore((state) => state.runBatch)
  const cancelBatch = useImageConvertStore((state) => state.cancelBatch)
  const finalizeBatch = useImageConvertStore((state) => state.finalizeBatch)
  const downloadZip = useImageConvertStore((state) => state.downloadZip)

  const { events, latestEvent } = useJobProgress(jobId)

  useEffect(() => {
    if (!latestEvent || !jobId) return
    if (latestEvent.type === 'completed' || latestEvent.type === 'failed') {
      void finalizeBatch()
    }
  }, [latestEvent, jobId, finalizeBatch])

  const progress = useMemo(() => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index]
      if (event.total === null) continue
      if (event.type !== 'progress' && event.type !== 'started') continue
      return { current: event.current ?? 0, total: event.total, detail: event.detail ?? '' }
    }
    return null
  }, [events])

  const canRun = images.length > 0 && !isRunning

  return (
    <div className="batch-layout">
      <aside className="batch-setup panel panel--form">
        <h2 className="column__title">Imágenes de entrada</h2>
        <AppButton
          type="button"
          variant="outline"
          icon={ImagePlus}
          onClick={() => void selectImages()}
          disabled={isRunning}
        >
          Seleccionar imágenes
        </AppButton>
        {images.length === 0 ? (
          <p className="muted">Ninguna imagen seleccionada.</p>
        ) : (
          <ul className="multi-export-image-list">
            {images.map((path) => (
              <li key={path} className="multi-export-image-list__item" title={path}>
                <span className="multi-export-image-list__name">{basename(path)}</span>
                <AppButton
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  icon={X}
                  aria-label={`Quitar ${basename(path)}`}
                  onClick={() => removeImage(path)}
                  disabled={isRunning}
                />
              </li>
            ))}
          </ul>
        )}

        <h2 className="column__title">Formato</h2>
        <FormatOptions disabled={isRunning} />
      </aside>

      <div className="batch-stage">
        <section className="panel">
          <div className="multi-export-run-row">
            <p className="muted">{images.length} imagen(es) a convertir</p>
            <div className="multi-export-run-row__actions">
              {isRunning ? (
                <AppButton type="button" variant="outline" onClick={() => void cancelBatch()}>
                  Cancelar
                </AppButton>
              ) : null}
              <AppButton
                type="button"
                onClick={() => void runBatch()}
                disabled={!canRun}
                icon={isRunning ? Loader2 : undefined}
                iconClassName={isRunning ? 'animate-spin' : undefined}
              >
                {isRunning ? 'Convirtiendo…' : 'Convertir lote'}
              </AppButton>
            </div>
          </div>
          {isRunning && progress ? (
            <ProgressBar
              current={progress.current}
              total={progress.total}
              label={
                <span className="truncate font-medium text-foreground">
                  {basename(progress.detail)}
                </span>
              }
            />
          ) : null}
        </section>

        {batchResult ? (
          <section className="panel">
            <h2 className="column__title">Resultado</h2>
            <p className="muted">
              {batchResult.produced} / {batchResult.expected} imágenes convertidas
            </p>
            {batchResult.produced < batchResult.expected ? (
              <p className="warning" role="status">
                Algunas imágenes fallaron — revisa el detalle abajo.
              </p>
            ) : null}
            <AppButton type="button" variant="outline" icon={Download} onClick={() => void downloadZip()}>
              Descargar .zip
            </AppButton>
            <ul className="multi-export-result-list">
              {batchResult.items.map((item, index) => (
                <li
                  key={`${item.input ?? 'unknown'}-${index}`}
                  className={
                    item.status === 'failed'
                      ? 'multi-export-result-item multi-export-result-item--failed'
                      : 'multi-export-result-item'
                  }
                >
                  <span>{basename(item.input ?? '?')}</span>
                  <span>{item.status === 'succeeded' ? 'OK' : (item.error ?? 'Error')}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  )
}

export function ImageConvertPanel() {
  const mode = useImageConvertStore((state) => state.mode)
  const error = useImageConvertStore((state) => state.error)
  const setMode = useImageConvertStore((state) => state.setMode)

  return (
    <div
      role="tabpanel"
      id="panel-image-convert"
      aria-labelledby="tab-image-convert"
      className="flex h-full min-h-0 flex-col gap-3"
    >
      <div className="flex-none">
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          value={mode}
          onValueChange={(value) => {
            if (value === 'single' || value === 'batch') setMode(value)
          }}
          aria-label="Modo de conversión"
        >
          {MODE_OPTIONS.map((option) => (
            <ToggleGroupItem key={option.id} value={option.id} className="px-6">
              {option.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      {error ? (
        <p className="error flex-none" role="alert">
          {error}
        </p>
      ) : null}

      <div className="min-h-0 flex-1">{mode === 'single' ? <SingleMode /> : <BatchMode />}</div>
    </div>
  )
}
