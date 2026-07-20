import { Field, FieldLabel } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'

import type { ProviderInfo } from '../api/types'

interface ProviderSelectorProps {
  label: string
  value: string
  providers: ProviderInfo[]
  onChange: (value: string) => void
  disabled?: boolean
}

/** Selector de provider primitivo (LLM o imagen) según el catálogo del backend. */
export function ProviderSelector({ label, value, providers, onChange, disabled }: ProviderSelectorProps) {
  return (
    <Field>
      <FieldLabel>{label}</FieldLabel>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {providers.map((provider) => (
              <SelectItem key={provider.id} value={provider.id} disabled={!provider.available}>
                {provider.label}
                {!provider.available ? ' (no disponible)' : ''}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  )
}
