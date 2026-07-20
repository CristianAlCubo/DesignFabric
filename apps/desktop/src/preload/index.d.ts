export {}

import type { LogEntry } from '@shared/logEntry'
import type { SetupPreferences } from '@shared/setupPreferences'

declare global {
  interface Window {
    designfabricv2: {
      getBackendBaseUrl: () => Promise<string>

      /** Historial de logs acumulado (ring buffer de 2000 entradas) del proceso main + backend. */
      getLogHistory: () => Promise<LogEntry[]>

      /** Se suscribe a nuevas entradas de log en tiempo real. Devuelve una función de desuscripción. */
      onLog: (callback: (entry: LogEntry) => void) => () => void

      /** Diálogo nativo para elegir una única imagen. `undefined` si el usuario cancela. */
      openImageDialog: () => Promise<string | undefined>

      /** Diálogo nativo para elegir varias imágenes. Array vacío si el usuario cancela. */
      openImagesDialog: () => Promise<string[]>

      /** Diálogo nativo para elegir un directorio. `undefined` si el usuario cancela. */
      openDirectoryDialog: () => Promise<string | undefined>

      /** Convierte una imagen local en disco a data URL (el CSP no permite `file://`). */
      getImagePreview: (filePath: string) => Promise<string>

      /**
       * Guarda vía diálogo nativo la imagen servida en `sourceUrl` (URL local del backend,
       * ej. `http://127.0.0.1:PORT/output/...`) con `suggestedName` como nombre por defecto.
       * `undefined` si el usuario cancela.
       */
      exportImage: (sourceUrl: string, suggestedName: string) => Promise<string | undefined>

      /** Abre una ruta (archivo o carpeta) en el explorador de archivos del SO. */
      openPath: (targetPath: string) => Promise<string>

      /** Preferencias del wizard de primer arranque (en dev, siempre "completado"). */
      getSetupPreferences: () => Promise<SetupPreferences>

      /** Persiste la elección del wizard y arranca el backend con los extras correspondientes. */
      completeWizard: (choice: 'installed' | 'deferred') => Promise<SetupPreferences>

      /** Instala el módulo de IA local diferido: reinicia el backend con el extra `local-ai`. */
      installLocalAiLater: () => Promise<void>
    }
  }
}
