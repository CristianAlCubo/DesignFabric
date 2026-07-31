import { Trash2 } from 'lucide-react'

import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

import { AppButton } from '../../core/components/AppButton'
import type { SizeMode, SizeRow } from '@shared/multiExportPresets'
import { isSizeRowValid } from './sizeRowValidation'
import { SizeSwatch } from './SizeSwatch'

interface SizeRowEditorProps {
  row: SizeRow
  disabled?: boolean
  onChange: (patch: Partial<SizeRow>) => void
  onRemove: () => void
}

function numberOrNull(value: string): number | null {
  if (value.trim() === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/** Editor de una fila de tamaño (px fijo o porcentual) dentro de un preset ad-hoc o guardado. */
export function SizeRowEditor({ row, disabled, onChange, onRemove }: SizeRowEditorProps) {
  const valid = isSizeRowValid(row)

  function handleModeChange(value: string) {
    if (value === 'px') onChange({ mode: 'px', percent: null })
    else if (value === 'percent') onChange({ mode: 'percent', width: null, height: null })
  }

  return (
    <div
      className={
        valid
          ? 'flex flex-col gap-3 rounded-lg border border-border bg-card p-3'
          : 'flex flex-col gap-3 rounded-lg border border-destructive/50 bg-card p-3'
      }
    >
      <div className="flex items-center gap-3">
        <SizeSwatch row={row} />
        <Input
          value={row.label}
          onChange={(event) => onChange({ label: event.target.value })}
          placeholder="Nombre del tamaño"
          disabled={disabled}
          className="min-w-0 flex-1"
        />
        <AppButton
          type="button"
          variant="ghost"
          size="icon"
          icon={Trash2}
          aria-label="Quitar tamaño"
          onClick={onRemove}
          disabled={disabled}
        />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <ToggleGroup
          type="single"
          variant="outline"
          spacing={0}
          className="w-auto"
          value={row.mode}
          onValueChange={(value) => {
            if (value) handleModeChange(value as SizeMode)
          }}
          disabled={disabled}
          aria-label="Modo de tamaño"
        >
          <ToggleGroupItem value="px">Píxeles</ToggleGroupItem>
          <ToggleGroupItem value="percent">Porcentaje</ToggleGroupItem>
        </ToggleGroup>

        {row.mode === 'px' ? (
          <>
            <Field className="w-24">
              <FieldLabel>Ancho (px)</FieldLabel>
              <Input
                type="number"
                min={1}
                placeholder="Auto"
                value={row.width ?? ''}
                onChange={(event) => onChange({ width: numberOrNull(event.target.value) })}
                disabled={disabled}
              />
            </Field>
            <Field className="w-24">
              <FieldLabel>Alto (px)</FieldLabel>
              <Input
                type="number"
                min={1}
                placeholder="Auto"
                value={row.height ?? ''}
                onChange={(event) => onChange({ height: numberOrNull(event.target.value) })}
                disabled={disabled}
              />
            </Field>
          </>
        ) : (
          <Field className="w-28">
            <FieldLabel>Porcentaje</FieldLabel>
            <Input
              type="number"
              min={1}
              step="any"
              placeholder="50"
              value={row.percent ?? ''}
              onChange={(event) => onChange({ percent: numberOrNull(event.target.value) })}
              disabled={disabled}
            />
          </Field>
        )}

        <Field className="w-28">
          <FieldLabel>Prefijo</FieldLabel>
          <Input
            value={row.prefix}
            onChange={(event) => onChange({ prefix: event.target.value })}
            placeholder="thumb_"
            disabled={disabled}
          />
        </Field>
        <Field className="min-w-40 flex-1">
          <FieldLabel>Plantilla (opcional)</FieldLabel>
          <Input
            value={row.template ?? ''}
            onChange={(event) => onChange({ template: event.target.value || null })}
            placeholder="{prefix}{name}"
            disabled={disabled}
          />
        </Field>
      </div>

      {!valid ? <p className="text-xs text-destructive">Completa el nombre y el tamaño de esta fila.</p> : null}
    </div>
  )
}
