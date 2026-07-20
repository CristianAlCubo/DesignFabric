import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

import { app } from 'electron'

const STORE_PATH = join(app.getPath('userData'), 'last-image-directory.json')

interface LastImageDirectoryStore {
  directory: string
}

/** Devuelve el último directorio usado para elegir/exportar una imagen, si existe. */
export function getLastImageDirectory(): string | undefined {
  try {
    if (!existsSync(STORE_PATH)) return undefined
    const raw = readFileSync(STORE_PATH, 'utf-8')
    const parsed = JSON.parse(raw) as LastImageDirectoryStore
    return parsed.directory
  } catch {
    return undefined
  }
}

/** Recuerda el directorio que contiene `imagePath` para la próxima vez que se abra un diálogo. */
export function rememberImageDirectory(imagePath: string): void {
  try {
    const directory = dirname(imagePath)
    mkdirSync(dirname(STORE_PATH), { recursive: true })
    writeFileSync(STORE_PATH, JSON.stringify({ directory } satisfies LastImageDirectoryStore))
  } catch {
    // No es crítico si no se puede persistir; simplemente no se recordará.
  }
}
