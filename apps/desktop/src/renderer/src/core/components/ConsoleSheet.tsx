import { useEffect, useId, useRef } from 'react'
import { X } from 'lucide-react'

import { LogConsole } from './LogConsole'

interface ConsoleSheetProps {
  open: boolean
  onClose: () => void
}

export function ConsoleSheet({ open, onClose }: ConsoleSheetProps) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return

    const previous = document.activeElement as HTMLElement | null
    closeRef.current?.focus()

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !panelRef.current) return

      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      previous?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="console-sheet" id="console-sheet">
      <button
        type="button"
        className="console-sheet__backdrop"
        aria-label="Cerrar consola"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        className="console-sheet__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="console-sheet__header">
          <h2 id={titleId} className="console-sheet__title">
            Registro
          </h2>
          <button
            ref={closeRef}
            type="button"
            className="console-sheet__close"
            aria-label="Cerrar consola"
            onClick={onClose}
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
        </header>
        <div className="console-sheet__body">
          <LogConsole />
        </div>
      </div>
    </div>
  )
}
