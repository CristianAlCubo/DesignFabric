import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

interface ModelSelectorProps {
  value: string
  onChange: (value: string) => void
}

/** Input de texto libre para el modelo de Ollama (sin listado dinámico por ahora). */
export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  return (
    <Field>
      <FieldLabel htmlFor="ollama-model">Modelo de Ollama</FieldLabel>
      <Input
        id="ollama-model"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="gemma3:4b"
      />
    </Field>
  )
}
