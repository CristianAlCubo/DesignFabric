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
    <label className="field">
      <span>{label}</span>
      <select
        className="field__input"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {providers.map((provider) => (
          <option key={provider.id} value={provider.id} disabled={!provider.available}>
            {provider.label}
            {!provider.available ? ' (no disponible)' : ''}
          </option>
        ))}
      </select>
    </label>
  )
}
