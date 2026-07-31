import { useEffect, useMemo, useState } from 'react'
import { BookmarkPlus, Download, ImagePlus, Loader2, Plus, Settings2, X } from 'lucide-react'

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

import type { SizeRow } from '@shared/multiExportPresets'

import { AppButton } from '../../core/components/AppButton'
import { ProgressBar } from '../../core/components/ProgressBar'
import { useJobProgress } from '../../core/hooks/useJobProgress'
import { PresetManagerDialog } from './PresetManagerDialog'
import { isSizeRowValid } from './sizeRowValidation'
import { SizeRowEditor } from './SizeRowEditor'
import { useMultiExportStore } from './store'

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

/** Radix `Select` no admite `value=""`/`null`; este sentinel representa "sin preset (ad-hoc)". */
const NO_PRESET_VALUE = '__no-preset__'

interface ManagerState {
  mode: 'browse' | 'create'
  draft?: { sizes: SizeRow[] }
}

export function MultiExportPanel() {
  const images = useMultiExportStore((state) => state.images)
  const presets = useMultiExportStore((state) => state.presets)
  const selectedPresetId = useMultiExportStore((state) => state.selectedPresetId)
  const activeSizes = useMultiExportStore((state) => state.activeSizes)
  const jobId = useMultiExportStore((state) => state.jobId)
  const result = useMultiExportStore((state) => state.result)
  const error = useMultiExportStore((state) => state.error)
  const isRunning = useMultiExportStore((state) => state.isRunning)

  const loadPresets = useMultiExportStore((state) => state.loadPresets)
  const selectImages = useMultiExportStore((state) => state.selectImages)
  const removeImage = useMultiExportStore((state) => state.removeImage)
  const selectPreset = useMultiExportStore((state) => state.selectPreset)
  const addSizeRow = useMultiExportStore((state) => state.addSizeRow)
  const updateSizeRow = useMultiExportStore((state) => state.updateSizeRow)
  const removeSizeRow = useMultiExportStore((state) => state.removeSizeRow)
  const runExport = useMultiExportStore((state) => state.runExport)
  const cancelExport = useMultiExportStore((state) => state.cancelExport)
  const finalizeJob = useMultiExportStore((state) => state.finalizeJob)
  const downloadZip = useMultiExportStore((state) => state.downloadZip)

  const [manager, setManager] = useState<ManagerState | null>(null)

  const { events, latestEvent } = useJobProgress(jobId)

  useEffect(() => {
    void loadPresets()
  }, [loadPresets])

  useEffect(() => {
    if (!latestEvent || !jobId) return
    if (latestEvent.type === 'completed' || latestEvent.type === 'failed') {
      void finalizeJob()
    }
  }, [latestEvent, jobId, finalizeJob])

  const progress = useMemo(() => {
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index]
      if (event.total === null) continue
      if (event.type !== 'progress' && event.type !== 'started') continue
      return { current: event.current ?? 0, total: event.total, detail: event.detail ?? '' }
    }
    return null
  }, [events])

  // El backend emite el progreso por combinación (imagen × tamaño) con la ruta de la imagen
  // en curso como `detail` — como `images` es el mismo arreglo enviado al job, su índice ahí
  // nos dice en qué imagen del lote va la corrida sin tener que asumir nada sobre el orden.
  const currentImageNumber = useMemo(() => {
    if (!progress?.detail) return null
    const index = images.indexOf(progress.detail)
    return index >= 0 ? index + 1 : null
  }, [progress, images])

  const builtinPresets = presets.filter((preset) => preset.isBuiltin)
  const userPresets = presets.filter((preset) => !preset.isBuiltin)

  const totalOutputs = images.length * activeSizes.length
  const canRun =
    images.length > 0 && activeSizes.length > 0 && activeSizes.every(isSizeRowValid) && !isRunning

  return (
    <div className="batch-layout" role="tabpanel" id="panel-multi-export" aria-labelledby="tab-multi-export">
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

        <h2 className="column__title">Preset</h2>
        <Select
          value={selectedPresetId ?? NO_PRESET_VALUE}
          onValueChange={(value) => selectPreset(value === NO_PRESET_VALUE ? null : value)}
          disabled={isRunning}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={NO_PRESET_VALUE}>Sin preset (ad-hoc)</SelectItem>
            {builtinPresets.length > 0 ? (
              <SelectGroup>
                <SelectLabel>De fábrica</SelectLabel>
                {builtinPresets.map((preset) => (
                  <SelectItem key={preset.id} value={preset.id}>
                    {preset.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            ) : null}
            {userPresets.length > 0 ? (
              <SelectGroup>
                <SelectLabel>Tus presets</SelectLabel>
                {userPresets.map((preset) => (
                  <SelectItem key={preset.id} value={preset.id}>
                    {preset.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            ) : null}
          </SelectContent>
        </Select>
        <AppButton
          type="button"
          variant="outline"
          icon={Settings2}
          onClick={() => setManager({ mode: 'browse' })}
          disabled={isRunning}
        >
          Administrar presets…
        </AppButton>

        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
      </aside>

      <div className="batch-stage">
        <section className="panel">
          <div className="multi-export-run-row">
            <p className="muted">
              {images.length} imagen(es) × {activeSizes.length} tamaño(s) = {totalOutputs} archivo(s)
            </p>
            <div className="multi-export-run-row__actions">
              {isRunning ? (
                <AppButton type="button" variant="outline" onClick={() => void cancelExport()}>
                  Cancelar
                </AppButton>
              ) : null}
              <AppButton
                type="button"
                onClick={() => void runExport()}
                disabled={!canRun}
                icon={isRunning ? Loader2 : undefined}
                iconClassName={isRunning ? 'animate-spin' : undefined}
              >
                {isRunning ? 'Exportando…' : 'Exportar'}
              </AppButton>
            </div>
          </div>
          {isRunning && progress ? (
            <ProgressBar
              current={progress.current}
              total={progress.total}
              label={
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium text-foreground">{basename(progress.detail)}</span>
                  {currentImageNumber !== null ? (
                    <span className="shrink-0 text-xs text-muted-foreground">
                      Imagen {currentImageNumber} de {images.length}
                    </span>
                  ) : null}
                </div>
              }
            />
          ) : null}
        </section>

        <section className="panel flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="column__title">Tamaños de esta exportación</h2>
            <AppButton
              type="button"
              variant="outline"
              size="sm"
              icon={BookmarkPlus}
              onClick={() => setManager({ mode: 'create', draft: { sizes: activeSizes } })}
              disabled={isRunning || activeSizes.length === 0}
            >
              Guardar como preset…
            </AppButton>
          </div>
          <div className="flex max-h-80 flex-col gap-2 overflow-y-auto pr-1">
            {activeSizes.map((row) => (
              <SizeRowEditor
                key={row.id}
                row={row}
                disabled={isRunning}
                onChange={(patch) => updateSizeRow(row.id, patch)}
                onRemove={() => removeSizeRow(row.id)}
              />
            ))}
          </div>
          <AppButton type="button" variant="outline" icon={Plus} onClick={addSizeRow} disabled={isRunning}>
            Agregar tamaño
          </AppButton>
        </section>

        {result ? (
          <section className="panel">
            <h2 className="column__title">Resultado</h2>
            <p className="muted">
              {result.produced} / {result.expected} archivos generados
            </p>
            {result.produced < result.expected ? (
              <p className="warning" role="status">
                Algunas combinaciones fallaron — revisa el detalle abajo.
              </p>
            ) : null}
            <AppButton type="button" variant="outline" icon={Download} onClick={() => void downloadZip()}>
              Descargar .zip
            </AppButton>
            <ul className="multi-export-result-list">
              {result.items.map((item, index) => (
                <li
                  key={`${item.input ?? 'unknown'}-${item.size_label}-${index}`}
                  className={
                    item.status === 'failed'
                      ? 'multi-export-result-item multi-export-result-item--failed'
                      : 'multi-export-result-item'
                  }
                >
                  <span>{basename(item.input ?? '?')}</span>
                  <span className="muted">{item.size_label}</span>
                  <span>{item.status === 'succeeded' ? 'OK' : (item.error ?? 'Error')}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>

      <PresetManagerDialog
        open={manager !== null}
        onOpenChange={(open) => {
          if (!open) setManager(null)
        }}
        initialMode={manager?.mode}
        initialDraft={manager?.draft}
        onPresetCreated={
          manager?.mode === 'create'
            ? (preset) => {
                selectPreset(preset.id)
                setManager(null)
              }
            : undefined
        }
      />
    </div>
  )
}
