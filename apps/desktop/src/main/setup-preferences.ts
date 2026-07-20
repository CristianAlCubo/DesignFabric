/**
 * Preferencias del wizard de primer arranque (Fase 3+).
 *
 * Persiste si el usuario ya completó el wizard de bienvenida y qué eligió
 * respecto del módulo de IA local (instalarlo de inmediato, dejarlo para
 * después, o `null` si todavía no se le preguntó). `bootstrap()` en
 * `index.ts` usa `wizardCompleted` para decidir si arrancar el backend de
 * inmediato o esperar a que el renderer complete el wizard (Fase 5).
 *
 * Mismo patrón de persistencia simple en `userData` que
 * `lastImageDirectory.ts`, pero con escritura atómica (tmp + rename) porque
 * este archivo es más sensible a corrupción parcial.
 */

import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { app } from 'electron'

import type { SetupPreferences } from '@shared/setupPreferences'

const DEFAULT_PREFS: SetupPreferences = { wizardCompleted: false, localAiChoice: null, version: 1 }

function prefsPath(): string {
  return join(app.getPath('userData'), 'setup-preferences.json')
}

/** Lee las preferencias del wizard, o los valores por defecto si no existen o están corruptas. */
export function readSetupPreferences(): SetupPreferences {
  try {
    const target = prefsPath()
    if (!existsSync(target)) return DEFAULT_PREFS
    const raw = readFileSync(target, 'utf-8')
    const parsed = JSON.parse(raw) as Partial<SetupPreferences>
    return { ...DEFAULT_PREFS, ...parsed }
  } catch {
    return DEFAULT_PREFS
  }
}

/** Escribe las preferencias del wizard de forma atómica (tmp + rename). */
export function writeSetupPreferences(prefs: SetupPreferences): void {
  try {
    const target = prefsPath()
    const tmp = `${target}.tmp`
    writeFileSync(tmp, JSON.stringify(prefs, null, 2), 'utf-8')
    renameSync(tmp, target)
  } catch {
    // No es crítico si no se puede persistir; en el peor caso se vuelve a
    // preguntar en el próximo arranque.
  }
}
