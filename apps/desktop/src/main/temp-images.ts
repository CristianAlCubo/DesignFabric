/**
 * Archivos temporales de imágenes pegadas/soltadas (Ctrl+V y drag & drop).
 *
 * El backend procesa rutas de archivo (`input_path`), pero el portapapeles y el
 * arrastrar-y-soltar entregan bytes sin ruta. Este módulo materializa esos bytes
 * en un archivo temporal en disco y devuelve su ruta, validando primero que sean
 * una imagen soportada (PNG/JPEG/WEBP) por *magic bytes* — no por la extensión ni
 * el mime declarado, que el portapapeles omite o falsea.
 *
 * Ciclo de vida (ver design.md — Decisión 2):
 * - Cada input mantiene ≤1 temporal: el renderer llama `disposeTempImage` del
 *   anterior al adquirir uno nuevo.
 * - `sweepTempImages()` en el arranque (red de seguridad ante un crash previo).
 * - `cleanupAllTempImages()` en el cierre borra todo lo aún registrado.
 */
import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readdirSync, rmSync } from 'node:fs'
import { unlink, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import { app } from 'electron'

/** Formatos soportados, alineados con el diálogo nativo y el backend. */
interface DetectedFormat {
  ext: string
  mime: string
}

/** Registro autoritativo (en memoria) de las rutas temporales vivas. */
const liveTempPaths = new Set<string>()

/** Subdirectorio propio bajo el temp del SO, para poder barrerlo entero sin tocar nada ajeno. */
function tempDir(): string {
  return join(app.getPath('temp'), 'designfabric-clipboard')
}

/**
 * Detecta el formato por magic bytes. Devuelve `null` si no es una imagen soportada
 * — ese `null` es lo que hace que "no pase nada" al pegar/soltar contenido no-imagen.
 */
function detectImageFormat(buffer: Buffer): DetectedFormat | null {
  // PNG: 89 50 4E 47 0D 0A 1A 0A
  if (
    buffer.length >= 8 &&
    buffer[0] === 0x89 &&
    buffer[1] === 0x50 &&
    buffer[2] === 0x4e &&
    buffer[3] === 0x47
  ) {
    return { ext: '.png', mime: 'image/png' }
  }
  // JPEG: FF D8 FF
  if (buffer.length >= 3 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff) {
    return { ext: '.jpg', mime: 'image/jpeg' }
  }
  // WEBP: "RIFF"...."WEBP"
  if (
    buffer.length >= 12 &&
    buffer.toString('ascii', 0, 4) === 'RIFF' &&
    buffer.toString('ascii', 8, 12) === 'WEBP'
  ) {
    return { ext: '.webp', mime: 'image/webp' }
  }
  return null
}

export interface TempImageResult {
  path: string
  previewUrl: string
}

/**
 * Escribe `bytes` como archivo temporal si son una imagen soportada.
 * Devuelve `{ path, previewUrl }`, o `null` si la validación falla (no es imagen).
 */
export async function writeTempImage(bytes: ArrayBuffer): Promise<TempImageResult | null> {
  const buffer = Buffer.from(bytes)
  const format = detectImageFormat(buffer)
  if (!format) return null

  const dir = tempDir()
  mkdirSync(dir, { recursive: true })
  const filePath = join(dir, `paste-${randomUUID()}${format.ext}`)
  await writeFile(filePath, buffer)
  liveTempPaths.add(filePath)

  return {
    path: filePath,
    previewUrl: `data:${format.mime};base64,${buffer.toString('base64')}`
  }
}

/**
 * Borra un temporal creado por `writeTempImage`. No-op si la ruta no está en el
 * registro (p. ej. una ruta del diálogo nativo o de otra pestaña).
 */
export async function disposeTempImage(filePath: string): Promise<void> {
  if (!liveTempPaths.has(filePath)) return
  liveTempPaths.delete(filePath)
  try {
    await unlink(filePath)
  } catch {
    // Ya no existía: idempotente.
  }
}

/** Barre el subdirectorio temporal completo al arrancar (limpia restos de un crash previo). */
export function sweepTempImages(): void {
  const dir = tempDir()
  if (!existsSync(dir)) return
  for (const entry of readdirSync(dir)) {
    try {
      rmSync(join(dir, entry), { force: true })
    } catch {
      // Ignorar: un archivo bloqueado no debe impedir el arranque.
    }
  }
  liveTempPaths.clear()
}

/** Borra todos los temporales aún registrados. Llamar en el cierre de la app (síncrono). */
export function cleanupAllTempImages(): void {
  for (const filePath of liveTempPaths) {
    try {
      rmSync(filePath, { force: true })
    } catch {
      // Ignorar en el cierre.
    }
  }
  liveTempPaths.clear()
}
