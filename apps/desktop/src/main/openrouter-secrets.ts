/**
 * Persistencia cifrada de la API key de OpenRouter vía Electron safeStorage.
 */

import { existsSync, readFileSync, renameSync, unlinkSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { app, safeStorage } from 'electron'

function secretsPath(): string {
  return join(app.getPath('userData'), 'openrouter-api-key.bin')
}

export function isOpenRouterEncryptionAvailable(): boolean {
  return safeStorage.isEncryptionAvailable()
}

export function readOpenRouterApiKey(): string | null {
  try {
    const target = secretsPath()
    if (!existsSync(target)) return null
    if (!safeStorage.isEncryptionAvailable()) return null
    const encrypted = readFileSync(target)
    return safeStorage.decryptString(encrypted)
  } catch {
    return null
  }
}

export function writeOpenRouterApiKey(apiKey: string): void {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error(
      'El cifrado seguro no está disponible en este sistema. No se puede guardar la API key.'
    )
  }
  const stripped = apiKey.trim()
  if (!stripped) {
    clearOpenRouterApiKey()
    return
  }
  const encrypted = safeStorage.encryptString(stripped)
  const target = secretsPath()
  const tmp = `${target}.tmp`
  writeFileSync(tmp, encrypted)
  renameSync(tmp, target)
}

export function clearOpenRouterApiKey(): void {
  const target = secretsPath()
  try {
    if (existsSync(target)) unlinkSync(target)
  } catch {
    // ignore
  }
}

export function maskApiKey(apiKey: string | null): string | null {
  if (!apiKey) return null
  const value = apiKey.trim()
  if (value.length <= 8) return '••••••••'
  return `${value.slice(0, 6)}…${value.slice(-4)}`
}
