import { useEffect, useState } from 'react'
import { FileBox, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'

import type { ModelPathPreferences } from '@shared/modelPathPreferences'

import { getSettingsSection } from './sections'

type ModelPathKey = keyof Pick<
  ModelPathPreferences,
  'sam2EncoderOnnxPath' | 'sam2DecoderOnnxPath' | 'vitMatteOnnxPath' | 'isnetGeneralOnnxPath'
>

function basename(filePath: string): string {
  const parts = filePath.split(/[/\\]/)
  return parts[parts.length - 1] || filePath
}

function ModelPathField({
  label,
  description,
  path,
  saving,
  clearLabel,
  onPick,
  onClear
}: {
  label: string
  description: string
  path: string | null
  saving: boolean
  clearLabel: string
  onPick: () => void
  onClear: () => void
}) {
  return (
    <Field>
      <FieldLabel>{label}</FieldLabel>
      <FieldDescription>{description}</FieldDescription>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" disabled={saving} onClick={onPick}>
          <FileBox aria-hidden />
          {path ? basename(path) : 'Elegir archivo .onnx'}
        </Button>
        {path ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            disabled={saving}
            aria-label={clearLabel}
            onClick={onClear}
          >
            <X aria-hidden />
          </Button>
        ) : null}
      </div>
      {path ? (
        <p className="mt-1 break-all text-xs text-muted-foreground" title={path}>
          {path}
        </p>
      ) : null}
    </Field>
  )
}

export function LocalModelsSection() {
  const section = getSettingsSection('local-models')
  const [prefs, setPrefs] = useState<ModelPathPreferences | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void window.designfabric
      .getModelPaths()
      .then(setPrefs)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'No se pudieron cargar las rutas de modelos.')
      })
  }, [])

  async function persist(next: ModelPathPreferences): Promise<void> {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const saved = await window.designfabric.setModelPaths(next)
      setPrefs(saved)
      setMessage('Rutas de modelos guardadas.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron guardar las rutas.')
    } finally {
      setSaving(false)
    }
  }

  async function pickPath(key: ModelPathKey): Promise<void> {
    if (!prefs) return
    const path = await window.designfabric.openOnnxFileDialog()
    if (!path) return
    await persist({ ...prefs, [key]: path })
  }

  async function clearPath(key: ModelPathKey): Promise<void> {
    if (!prefs) return
    await persist({ ...prefs, [key]: null })
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto px-6 py-5">
      <header className="mb-6 shrink-0">
        <h1 className="text-lg font-semibold tracking-tight text-foreground">{section.label}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{section.description}</p>
      </header>

      {prefs ? (
        <FieldGroup className="max-w-lg gap-5">
          <ModelPathField
            label="IS-Net (general) — ONNX"
            description="Recomendado por defecto para ilustraciones/stickers: segmentación de un solo paso, bordes duros y consistentes (p. ej. isnet-general-use.onnx)."
            path={prefs.isnetGeneralOnnxPath}
            saving={saving}
            clearLabel="Quitar ruta IS-Net"
            onPick={() => {
              void pickPath('isnetGeneralOnnxPath')
            }}
            onClear={() => {
              void clearPath('isnetGeneralOnnxPath')
            }}
          />

          <ModelPathField
            label="SAM2 Tiny — encoder (ONNX)"
            description="Primer archivo del par SAM2 (p. ej. sam2_hiera_tiny.encoder.onnx)."
            path={prefs.sam2EncoderOnnxPath}
            saving={saving}
            clearLabel="Quitar ruta del encoder SAM2"
            onPick={() => {
              void pickPath('sam2EncoderOnnxPath')
            }}
            onClear={() => {
              void clearPath('sam2EncoderOnnxPath')
            }}
          />

          <ModelPathField
            label="SAM2 Tiny — decoder (ONNX)"
            description="Segundo archivo del par SAM2 (p. ej. sam2_hiera_tiny.decoder.onnx)."
            path={prefs.sam2DecoderOnnxPath}
            saving={saving}
            clearLabel="Quitar ruta del decoder SAM2"
            onPick={() => {
              void pickPath('sam2DecoderOnnxPath')
            }}
            onClear={() => {
              void clearPath('sam2DecoderOnnxPath')
            }}
          />

          <ModelPathField
            label="ViTMatte (ONNX)"
            description="Modelo de matting que produce el canal alpha suave."
            path={prefs.vitMatteOnnxPath}
            saving={saving}
            clearLabel="Quitar ruta ViTMatte"
            onPick={() => {
              void pickPath('vitMatteOnnxPath')
            }}
            onClear={() => {
              void clearPath('vitMatteOnnxPath')
            }}
          />

          {message && <p className="text-sm text-muted-foreground">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </FieldGroup>
      ) : error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      )}
    </div>
  )
}
