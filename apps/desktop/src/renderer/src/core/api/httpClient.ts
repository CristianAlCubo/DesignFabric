/**
 * Cliente HTTP mínimo hacia el backend local único de DesignFabric. La URL
 * base se resuelve una sola vez (vía preload/IPC, ver `src/preload/index.ts`)
 * y se cachea en memoria para el resto de la sesión del renderer.
 */

let cachedBaseUrl: string | null = null

/** URL base del backend (ej. `http://127.0.0.1:8756`), resuelta vía IPC y cacheada. */
export async function getBackendBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return cachedBaseUrl
  cachedBaseUrl = await window.designfabric.getBackendBaseUrl()
  return cachedBaseUrl
}

export async function apiGet<T>(path: string): Promise<T> {
  const baseUrl = await getBackendBaseUrl()
  const response = await fetch(`${baseUrl}${path}`)
  if (!response.ok) throw new Error(`GET ${path} → ${response.status}`)
  return (await response.json()) as T
}

export async function apiPost<TBody, TResponse>(path: string, body: TBody): Promise<TResponse> {
  const baseUrl = await getBackendBaseUrl()
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!response.ok) throw new Error(`POST ${path} → ${response.status}`)
  return (await response.json()) as TResponse
}

export async function apiDelete(path: string): Promise<void> {
  const baseUrl = await getBackendBaseUrl()
  const response = await fetch(`${baseUrl}${path}`, { method: 'DELETE' })
  if (!response.ok && response.status !== 204) throw new Error(`DELETE ${path} → ${response.status}`)
}
