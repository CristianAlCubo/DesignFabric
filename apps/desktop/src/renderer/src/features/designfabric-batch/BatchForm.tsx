import { useState, type FormEvent } from 'react'

import { ModelSelector } from '../../core/components/ModelSelector'

interface BatchFormProps {
  onSubmit: (numImages: number, ollamaModel: string) => void
  isSubmitting: boolean
}

/** Formulario equivalente a los flags `--n`/`--ollama-model` del CLI. */
export function BatchForm({ onSubmit, isSubmitting }: BatchFormProps) {
  const [numImages, setNumImages] = useState(1)
  const [ollamaModel, setOllamaModel] = useState('gemma3:4b')

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    onSubmit(numImages, ollamaModel)
  }

  return (
    <form className="batch-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Número de stickers</span>
        <input
          type="number"
          min={1}
          max={50}
          value={numImages}
          onChange={(e) => setNumImages(Number(e.target.value))}
        />
      </label>
      <ModelSelector value={ollamaModel} onChange={setOllamaModel} />
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Generando…' : 'Generar'}
      </button>
    </form>
  )
}
