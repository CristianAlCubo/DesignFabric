import { TriangleAlert } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface ProviderAvailabilityWarningProps {
  title?: string
  messages: string[]
}

/** Aviso cuando un provider local/cloud no está listo para usarse. */
export function ProviderAvailabilityWarning({
  title = 'Provider no disponible',
  messages
}: ProviderAvailabilityWarningProps) {
  if (messages.length === 0) return null

  return (
    <Alert className="border-amber-500/40 text-amber-200">
      <TriangleAlert className="text-amber-400" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <ul className="mt-1 list-disc space-y-1 pl-4">
          {messages.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  )
}
