interface ModelSelectorProps {
  value: string
  onChange: (value: string) => void
}

/** Input de texto libre para el modelo de Ollama (sin listado dinámico por ahora). */
export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  return (
    <label className="field">
      <span>Modelo de Ollama</span>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="gemma3:4b" />
    </label>
  )
}
