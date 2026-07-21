/**
 * Preferencias de rutas locales a modelos ONNX (eliminación de fondo).
 */

export interface ModelPathPreferences {
  version: 3
  sam2EncoderOnnxPath: string | null
  sam2DecoderOnnxPath: string | null
  vitMatteOnnxPath: string | null
  isnetGeneralOnnxPath: string | null
}

export const DEFAULT_MODEL_PATH_PREFERENCES: ModelPathPreferences = {
  version: 3,
  sam2EncoderOnnxPath: null,
  sam2DecoderOnnxPath: null,
  vitMatteOnnxPath: null,
  isnetGeneralOnnxPath: null
}
