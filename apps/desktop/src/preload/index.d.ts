export {}

import type {
  GenerationPreferences,
  OpenRouterPublicStatus
} from '@shared/generationPreferences'
import type { LogEntry } from '@shared/logEntry'
import type { ModelPathPreferences } from '@shared/modelPathPreferences'
import type { MultiExportPreset, SizeRow } from '@shared/multiExportPresets'

declare global {
  interface Window {
    designfabric: {
      getBackendBaseUrl: () => Promise<string>

      /** Versión del producto leída desde el archivo VERSION (raíz del monorepo). */
      getAppVersion: () => Promise<string>

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

      /** Diálogo nativo para elegir un archivo ONNX. `undefined` si el usuario cancela. */
      openOnnxFileDialog: () => Promise<string | undefined>

      /** Cuenta imágenes soportadas (png/jpg/jpeg/webp) en una carpeta, sin subcarpetas. */
      countImagesInDirectory: (directoryPath: string) => Promise<number>

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

      /** Instala el módulo de IA local: reinicia el backend con el extra `local-ai`. */
      installLocalAiLater: () => Promise<void>

      /** Abre (o enfoca) la ventana hija de configuración. */
      openSettings: () => Promise<void>

      getOpenRouterStatus: () => Promise<OpenRouterPublicStatus>
      setOpenRouterKey: (apiKey: string) => Promise<OpenRouterPublicStatus>
      clearOpenRouterKey: () => Promise<OpenRouterPublicStatus>
      getGenerationPreferences: () => Promise<GenerationPreferences>
      setGenerationPreferences: (prefs: GenerationPreferences) => Promise<GenerationPreferences>
      getModelPaths: () => Promise<ModelPathPreferences>
      setModelPaths: (prefs: ModelPathPreferences) => Promise<ModelPathPreferences>

      /**
       * Guarda vía diálogo nativo el .zip generado por un job de exportación multi-tamaño
       * (URL local del backend). `undefined` si el usuario cancela.
       */
      downloadMultiExportZip: (sourceUrl: string, suggestedName: string) => Promise<string | undefined>

      /** Lista los presets de exportación multi-tamaño (built-in + de usuario). */
      listMultiExportPresets: () => Promise<MultiExportPreset[]>
      createMultiExportPreset: (input: { name: string; sizes: SizeRow[] }) => Promise<MultiExportPreset>
      updateMultiExportPreset: (
        id: string,
        patch: { name?: string; sizes?: SizeRow[] }
      ) => Promise<MultiExportPreset>
      deleteMultiExportPreset: (id: string) => Promise<void>
      duplicateMultiExportPreset: (id: string) => Promise<MultiExportPreset>

      /** Exporta uno o más presets a un archivo `.json` elegido por el usuario. */
      exportMultiExportPresetsToFile: (presets: MultiExportPreset[]) => Promise<string | undefined>

      /** Importa presets desde un archivo `.json` elegido por el usuario, validando su formato. */
      importMultiExportPresetsFromFile: () => Promise<MultiExportPreset[] | undefined>
    }
  }
}
