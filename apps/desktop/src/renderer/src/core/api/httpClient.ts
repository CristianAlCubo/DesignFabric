/**
 * Cliente HTTP mínimo hacia el backend local único de DesignFabric. La URL
 * base se resuelve una sola vez (vía preload/IPC, ver `src/preload/index.ts`)
 * y se cachea en memoria para el resto de la sesión del renderer.
 *
 * Antes de cada petición espera a que `GET /health` responda OK: la ventana
 * Electron se abre en paralelo al spawn del backend, así que sin este gate
 * los fetches iniciales fallan con "Failed to fetch".
 */

let cachedBaseUrl: string | null = null
let readyPromise: Promise<void> | null = null

const HEALTH_POLL_MS = 300
/** Alineado con el timeout generoso del proceso main (primer arranque empaquetado). */
const HEALTH_TIMEOUT_MS = 15 * 60 * 1000

/** URL base del backend (ej. `http://127.0.0.1:8756`), resuelta vía IPC y cacheada. */
export async function getBackendBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return cachedBaseUrl
  cachedBaseUrl = await window.designfabric.getBackendBaseUrl()
  return cachedBaseUrl
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError
}

function invalidateBackendReady(): void {
  readyPromise = null
}

/**
 * Espera (polling compartido) hasta que el backend responda en `/health`.
 * Las llamadas concurrentes reutilizan la misma promesa.
 */
export async function waitForBackendReady(timeoutMs = HEALTH_TIMEOUT_MS): Promise<void> {
  if (!readyPromise) {
    readyPromise = (async () => {
      const baseUrl = await getBackendBaseUrl()
      const start = Date.now()
      while (Date.now() - start < timeoutMs) {
        try {
          const response = await fetch(`${baseUrl}/health`)
          if (response.ok) return
        } catch {
          // El backend todavía no está escuchando; reintentar.
        }
        await sleep(HEALTH_POLL_MS)
      }
      throw new Error(`Backend did not become ready within ${timeoutMs}ms`)
    })().catch((err: unknown) => {
      invalidateBackendReady()
      throw err
    })
  }
  await readyPromise
}

async function withBackendReady<T>(request: () => Promise<T>): Promise<T> {
  await waitForBackendReady()
  try {
    return await request()
  } catch (err) {
    if (!isNetworkError(err)) throw err
    // Backend caído o reiniciando tras haber estado listo: volver a esperar y reintentar una vez.
    invalidateBackendReady()
    await waitForBackendReady()
    return await request()
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return withBackendReady(async () => {
    const baseUrl = await getBackendBaseUrl()
    const response = await fetch(`${baseUrl}${path}`)
    if (!response.ok) throw new Error(`GET ${path} → ${response.status}`)
    return (await response.json()) as T
  })
}

export async function apiPost<TBody, TResponse>(path: string, body: TBody): Promise<TResponse> {
  return withBackendReady(async () => {
    const baseUrl = await getBackendBaseUrl()
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!response.ok) throw new Error(`POST ${path} → ${response.status}`)
    return (await response.json()) as TResponse
  })
}

export async function apiDelete(path: string): Promise<void> {
  return withBackendReady(async () => {
    const baseUrl = await getBackendBaseUrl()
    const response = await fetch(`${baseUrl}${path}`, { method: 'DELETE' })
    if (!response.ok && response.status !== 204) throw new Error(`DELETE ${path} → ${response.status}`)
  })
}
