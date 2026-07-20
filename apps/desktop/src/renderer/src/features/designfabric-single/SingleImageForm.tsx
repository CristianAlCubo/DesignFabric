import { useState, type FormEvent } from 'react'

interface SingleImageFormProps {
  onSubmit: (prompt: string, applyStyleSuffix: boolean) => void
  isSubmitting: boolean
}

/** Formulario de la funcionalidad nueva: generar una imagen a partir de un prompt libre. */
export function SingleImageForm({ onSubmit, isSubmitting }: SingleImageFormProps) {
  const [prompt, setPrompt] = useState('')
  const [applyStyleSuffix, setApplyStyleSuffix] = useState(true)

  function handleSubmit(event: FormEvent): void {
    event.preventDefault()
    const trimmed = prompt.trim()
    if (!trimmed) return
    onSubmit(trimmed, applyStyleSuffix)
  }

  return (
    <form className="single-image-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Prompt</span>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="a grumpy owl perched on a stack of old books, wearing tiny reading glasses"
          rows={4}
        />
      </label>
      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={applyStyleSuffix}
          onChange={(e) => setApplyStyleSuffix(e.target.checked)}
        />
        <span>Aplicar estilo sticker (bordes gruesos, colores planos, fondo blanco)</span>
      </label>
      <button type="submit" disabled={isSubmitting || !prompt.trim()}>
        {isSubmitting ? 'Generando…' : 'Generar'}
      </button>
    </form>
  )
}
