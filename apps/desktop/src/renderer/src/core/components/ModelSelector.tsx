import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

interface ModelSelectorProps {
  value: string
  onChange: (value: string) => void
  models: string[]
  disabled?: boolean
  /** True si Ollama está reachable pero el valor elegido no está instalado. */
  modelMissing?: boolean
}

/** Selector de modelos locales reportados por Ollama (`/api/tags`). */
export function ModelSelector({
  value,
  onChange,
  models,
  disabled,
  modelMissing
}: ModelSelectorProps) {
  const options = models.length > 0 ? models : value ? [value] : []

  return (
    <Field>
      <FieldLabel htmlFor="ollama-model">Modelo de Ollama</FieldLabel>
      <Select
        value={value || undefined}
        onValueChange={onChange}
        disabled={disabled || models.length === 0}
      >
        <SelectTrigger id="ollama-model" className="w-full">
          <SelectValue placeholder={models.length === 0 ? 'Sin modelos instalados' : 'Elegí un modelo'} />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {options.map((model) => (
              <SelectItem key={model} value={model} disabled={!models.includes(model)}>
                {model}
                {!models.includes(model) ? ' (no instalado)' : ''}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      {models.length === 0 ? (
        <FieldDescription>No hay modelos en Ollama. Instalá uno fuera de la app por ahora.</FieldDescription>
      ) : null}
      {modelMissing ? (
        <FieldDescription className="text-destructive">
          El modelo seleccionado no está instalado en Ollama.
        </FieldDescription>
      ) : null}
    </Field>
  )
}
