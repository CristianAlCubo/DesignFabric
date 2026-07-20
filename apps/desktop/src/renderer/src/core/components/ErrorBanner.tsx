interface ErrorBannerProps {
  message: string
}

/** Aviso de error presentacional, usado cuando un job termina en estado `failed`. */
export function ErrorBanner({ message }: ErrorBannerProps) {
  return <div className="error-banner">⚠ {message}</div>
}
