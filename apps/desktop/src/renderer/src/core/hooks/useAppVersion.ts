import { useEffect, useState } from 'react'

/** Versión del producto expuesta por el proceso main (`VERSION`). */
export function useAppVersion(): string | null {
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void window.designfabric.getAppVersion().then((value) => {
      if (!cancelled) setVersion(value)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return version
}
