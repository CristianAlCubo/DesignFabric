/**
 * Tipos de las preferencias del wizard de primer arranque, compartidos entre
 * `main` (persistencia + IPC, ver `src/main/setup-preferences.ts` y
 * `src/main/setup-ipc.ts`) y `preload`/`renderer` (consumo vía
 * `window.designfabric`), sin acoplar `preload` al proceso `main`.
 */

export type LocalAiChoice = 'installed' | 'deferred' | null

export interface SetupPreferences {
  wizardCompleted: boolean
  localAiChoice: LocalAiChoice
  version: 1
}
