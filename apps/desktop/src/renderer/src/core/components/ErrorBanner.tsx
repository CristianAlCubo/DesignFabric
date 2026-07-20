import { Alert, AlertDescription } from '@/components/ui/alert'
import { CircleAlert } from 'lucide-react'

interface ErrorBannerProps {
  message: string
}

/** Aviso de error presentacional, usado cuando un job termina en estado `failed`. */
export function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  )
}
