import { useEffect, useMemo, useState } from 'react'
import { Copy, Download, Plus, Trash2, Upload } from 'lucide-react'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

import type { MultiExportPreset, SizeRow } from '@shared/multiExportPresets'

import { AppButton } from '../../core/components/AppButton'
import { isPresetDraftValid } from './sizeRowValidation'
import { SizeRowEditor } from './SizeRowEditor'
import { SizeSwatch } from './SizeSwatch'
import { createDefaultSizeRow, useMultiExportStore } from './store'

type Selection =
  | { kind: 'none' }
  | { kind: 'new'; name: string; sizes: SizeRow[] }
  | {
      kind: 'existing'
      presetId: string
      name: string
      sizes: SizeRow[]
      original: { name: string; sizes: SizeRow[] }
    }

interface PresetManagerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialMode?: 'browse' | 'create'
  initialDraft?: { name?: string; sizes: SizeRow[] }
  /** Solo se pasa cuando el modal se abre desde el atajo "Guardar como preset…" de la corrida. */
  onPresetCreated?: (preset: MultiExportPreset) => void
}

function toExisting(preset: MultiExportPreset): Selection {
  return {
    kind: 'existing',
    presetId: preset.id,
    name: preset.name,
    sizes: preset.sizes.map((row) => ({ ...row })),
    original: { name: preset.name, sizes: preset.sizes }
  }
}

/**
 * CRUD dedicado de presets: maestro-detalle sobre el mismo store del feature, pero con
 * selección y borrador propios (no comparte `selectedPresetId`/`activeSizes` de la corrida —
 * ver decisiones en el plan de rediseño).
 */
export function PresetManagerDialog({
  open,
  onOpenChange,
  initialMode = 'browse',
  initialDraft,
  onPresetCreated
}: PresetManagerDialogProps) {
  const presets = useMultiExportStore((state) => state.presets)
  const runSelectedPresetId = useMultiExportStore((state) => state.selectedPresetId)
  const error = useMultiExportStore((state) => state.error)
  const setError = useMultiExportStore((state) => state.setError)
  const createPreset = useMultiExportStore((state) => state.createPreset)
  const updatePreset = useMultiExportStore((state) => state.updatePreset)
  const deletePreset = useMultiExportStore((state) => state.deletePreset)
  const duplicatePreset = useMultiExportStore((state) => state.duplicatePreset)
  const exportPreset = useMultiExportStore((state) => state.exportPreset)
  const importPresets = useMultiExportStore((state) => state.importPresets)

  const [selection, setSelection] = useState<Selection>({ kind: 'none' })
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    if (initialMode === 'create') {
      setSelection({
        kind: 'new',
        name: initialDraft?.name ?? '',
        sizes: (initialDraft?.sizes ?? [createDefaultSizeRow()]).map((row) => ({ ...row }))
      })
      return
    }
    const current = presets.find((preset) => preset.id === runSelectedPresetId)
    setSelection(current ? toExisting(current) : { kind: 'none' })
    // Solo re-inicializar cuando el modal pasa a abierto — no en cada cambio de `presets`
    // (eso pisaría el borrador en curso cada vez que el usuario guarda otro preset).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const selectedPresetMeta = selection.kind === 'existing' ? presets.find((p) => p.id === selection.presetId) : undefined
  const isBuiltinSelected = Boolean(selectedPresetMeta?.isBuiltin)

  const canSave = useMemo(() => {
    if (selection.kind === 'none' || isBuiltinSelected) return false
    if (!isPresetDraftValid(selection.name, selection.sizes)) return false
    if (selection.kind === 'new') return true
    return (
      selection.name !== selection.original.name ||
      JSON.stringify(selection.sizes) !== JSON.stringify(selection.original.sizes)
    )
  }, [selection, isBuiltinSelected])

  function selectExisting(preset: MultiExportPreset) {
    setSelection(toExisting(preset))
  }

  function startNewDraft() {
    setSelection({ kind: 'new', name: '', sizes: [createDefaultSizeRow()] })
  }

  function updateDraftName(name: string) {
    setSelection((current) => (current.kind === 'none' ? current : { ...current, name }))
  }

  function addDraftRow() {
    setSelection((current) =>
      current.kind === 'none' ? current : { ...current, sizes: [...current.sizes, createDefaultSizeRow()] }
    )
  }

  function updateDraftRow(id: string, patch: Partial<SizeRow>) {
    setSelection((current) =>
      current.kind === 'none'
        ? current
        : { ...current, sizes: current.sizes.map((row) => (row.id === id ? { ...row, ...patch } : row)) }
    )
  }

  function removeDraftRow(id: string) {
    setSelection((current) =>
      current.kind === 'none' ? current : { ...current, sizes: current.sizes.filter((row) => row.id !== id) }
    )
  }

  async function handleSave() {
    if (selection.kind === 'new') {
      const preset = await createPreset({ name: selection.name.trim(), sizes: selection.sizes })
      if (!preset) return
      setSelection(toExisting(preset))
      onPresetCreated?.(preset)
      return
    }
    if (selection.kind === 'existing') {
      const updated = await updatePreset(selection.presetId, {
        name: selection.name.trim(),
        sizes: selection.sizes
      })
      if (!updated) return
      setSelection(toExisting(updated))
    }
  }

  async function handleDuplicate(id: string) {
    const copy = await duplicatePreset(id)
    if (!copy) return
    selectExisting(copy)
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    await deletePreset(pendingDelete.id)
    setPendingDelete(null)
    setSelection({ kind: 'none' })
  }

  async function handleImport() {
    const imported = await importPresets()
    if (!imported || imported.length === 0) return
    selectExisting(imported[0])
  }

  const builtinPresets = presets.filter((preset) => preset.isBuiltin)
  const userPresets = presets.filter((preset) => !preset.isBuiltin)
  const draftName = selection.kind === 'none' ? '' : selection.name
  const draftSizes = selection.kind === 'none' ? [] : selection.sizes

  function renderPresetRow(preset: MultiExportPreset) {
    const isSelected = selection.kind === 'existing' && selection.presetId === preset.id
    return (
      <button
        key={preset.id}
        type="button"
        onClick={() => selectExisting(preset)}
        className={cn(
          'flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-2 text-left text-sm hover:bg-accent/60',
          isSelected && 'border-primary/50 bg-accent'
        )}
      >
        <SizeSwatch row={preset.sizes[0] ?? { mode: 'px', width: null, height: null, percent: null }} size={28} />
        <span className="min-w-0 flex-1 truncate">{preset.name}</span>
        <span className="text-xs text-muted-foreground">{preset.sizes.length}</span>
      </button>
    )
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="flex max-h-[85vh] w-full flex-col gap-4 sm:max-w-[820px]">
          <DialogHeader>
            <DialogTitle>Administrar presets</DialogTitle>
            <DialogDescription>Crea, edita, duplica o elimina tus presets de tamaños.</DialogDescription>
          </DialogHeader>

          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <div className="flex min-h-0 flex-1 gap-4">
            <div className="flex min-h-0 w-60 shrink-0 flex-col gap-2 border-r border-border pr-4">
              <AppButton type="button" icon={Plus} variant="outline" className="w-full" onClick={startNewDraft}>
                Nuevo preset
              </AppButton>
              <AppButton type="button" icon={Upload} variant="ghost" size="sm" onClick={() => void handleImport()}>
                Importar…
              </AppButton>

              {presets.length === 0 ? (
                <p className="mt-4 text-sm text-muted-foreground">
                  Todavía no tienes presets. Crea uno o impórtalos desde un archivo.
                </p>
              ) : (
                <ScrollArea className="-mr-2 min-h-0 flex-1 pr-2">
                  <div className="flex flex-col gap-1">
                    {builtinPresets.length > 0 ? (
                      <>
                        <p className="mt-1 px-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          De fábrica
                        </p>
                        {builtinPresets.map(renderPresetRow)}
                      </>
                    ) : null}
                    {userPresets.length > 0 ? (
                      <>
                        <p className="mt-2 px-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          Tus presets
                        </p>
                        {userPresets.map(renderPresetRow)}
                      </>
                    ) : null}
                  </div>
                </ScrollArea>
              )}
            </div>

            <div className="flex min-w-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
              {selection.kind === 'none' ? (
                <p className="text-sm text-muted-foreground">Selecciona un preset de la lista o crea uno nuevo.</p>
              ) : (
                <>
                  <Field>
                    <FieldLabel htmlFor="preset-manager-name">
                      Nombre
                      {isBuiltinSelected ? <Badge variant="outline">De fábrica</Badge> : null}
                    </FieldLabel>
                    <Input
                      id="preset-manager-name"
                      value={draftName}
                      disabled={isBuiltinSelected}
                      onChange={(event) => updateDraftName(event.target.value)}
                      placeholder="Nombre del preset"
                    />
                  </Field>

                  <div className="flex flex-col gap-2">
                    {draftSizes.map((row) => (
                      <SizeRowEditor
                        key={row.id}
                        row={row}
                        disabled={isBuiltinSelected}
                        onChange={(patch) => updateDraftRow(row.id, patch)}
                        onRemove={() => removeDraftRow(row.id)}
                      />
                    ))}
                    <AppButton
                      type="button"
                      variant="outline"
                      icon={Plus}
                      disabled={isBuiltinSelected}
                      onClick={addDraftRow}
                    >
                      Agregar tamaño
                    </AppButton>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <AppButton type="button" disabled={!canSave} onClick={() => void handleSave()}>
                      {selection.kind === 'new' ? 'Crear preset' : 'Guardar'}
                    </AppButton>
                    {selection.kind === 'existing' ? (
                      <>
                        <AppButton
                          type="button"
                          variant="outline"
                          icon={Copy}
                          onClick={() => void handleDuplicate(selection.presetId)}
                        >
                          Duplicar
                        </AppButton>
                        <AppButton
                          type="button"
                          variant="outline"
                          icon={Download}
                          onClick={() => void exportPreset(selection.presetId)}
                        >
                          Exportar…
                        </AppButton>
                        {!isBuiltinSelected ? (
                          <AppButton
                            type="button"
                            variant="outline"
                            icon={Trash2}
                            onClick={() =>
                              setPendingDelete({
                                id: selection.presetId,
                                name: selectedPresetMeta?.name ?? selection.name
                              })
                            }
                          >
                            Eliminar
                          </AppButton>
                        ) : null}
                      </>
                    ) : null}
                  </div>
                </>
              )}
            </div>
          </div>

          <DialogFooter>
            <AppButton type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cerrar
            </AppButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={pendingDelete !== null} onOpenChange={(nextOpen) => !nextOpen && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar preset?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará “{pendingDelete?.name}” de forma permanente. Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className={buttonVariants({ variant: 'destructive' })}
              onClick={() => void confirmDelete()}
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
