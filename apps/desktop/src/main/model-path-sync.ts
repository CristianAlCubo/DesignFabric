/**
 * Sincroniza rutas de modelos ONNX al backend (runtime config).
 */

import { backendBaseUrl } from './config'
import { pushLog } from './log-store'
import { readModelPathPreferences } from './model-path-preferences'

export async function syncModelPathsToBackend(): Promise<void> {
  const prefs = readModelPathPreferences()

  const body: Record<string, unknown> = {
    clear_sam2_encoder: !prefs.sam2EncoderOnnxPath,
    clear_sam2_decoder: !prefs.sam2DecoderOnnxPath,
    clear_vitmatte: !prefs.vitMatteOnnxPath,
    clear_isnet_general: !prefs.isnetGeneralOnnxPath
  }
  if (prefs.sam2EncoderOnnxPath) body.sam2_encoder_onnx = prefs.sam2EncoderOnnxPath
  if (prefs.sam2DecoderOnnxPath) body.sam2_decoder_onnx = prefs.sam2DecoderOnnxPath
  if (prefs.vitMatteOnnxPath) body.vitmatte_onnx = prefs.vitMatteOnnxPath
  if (prefs.isnetGeneralOnnxPath) body.isnet_general_onnx = prefs.isnetGeneralOnnxPath

  try {
    const response = await fetch(`${backendBaseUrl}/api/settings/model-paths`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!response.ok) {
      const detail = await response.text()
      pushLog({
        source: 'main',
        stream: 'error',
        line: `Model paths sync failed (${response.status}): ${detail}`
      })
    }
  } catch (err) {
    pushLog({
      source: 'main',
      stream: 'error',
      line: `Model paths sync error: ${String(err)}`
    })
  }
}

/** Env bootstrap para el spawn del backend (antes del PUT). */
export function modelPathEnvBootstrap(): Record<string, string> {
  const env: Record<string, string> = {}
  const prefs = readModelPathPreferences()
  if (prefs.sam2EncoderOnnxPath) {
    env.DESIGNFABRIC_SAM2_ENCODER_ONNX = prefs.sam2EncoderOnnxPath
  }
  if (prefs.sam2DecoderOnnxPath) {
    env.DESIGNFABRIC_SAM2_DECODER_ONNX = prefs.sam2DecoderOnnxPath
  }
  if (prefs.vitMatteOnnxPath) env.DESIGNFABRIC_VITMATTE_ONNX = prefs.vitMatteOnnxPath
  if (prefs.isnetGeneralOnnxPath) env.DESIGNFABRIC_ISNET_GENERAL_ONNX = prefs.isnetGeneralOnnxPath
  return env
}
