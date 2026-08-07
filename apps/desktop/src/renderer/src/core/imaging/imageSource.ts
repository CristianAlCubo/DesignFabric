/**
 * Modelo unificado de "fuente de imagen" de entrada.
 *
 * Una `ImageSource` abstrae de dónde vino la imagen (diálogo nativo, portapapeles,
 * arrastrar-y-soltar, o transferida desde otra pestaña) detrás de un contrato único:
 * una **ruta en disco** que el backend puede procesar y un **data URL de preview**
 * para mostrarla. El portapapeles y el drop entregan bytes sin ruta, así que se
 * materializan en un archivo temporal vía IPC (`writeTempImage`) antes de exponerlos.
 */

export type ImageOrigin = 'dialog' | 'clipboard' | 'drop' | 'transfer'

export interface ImageSource {
  /** Ruta de archivo legible por el backend (real en disco o temporal). */
  path: string
  /** Data URL o URL del backend para previsualizar. */
  previewUrl: string
  origin: ImageOrigin
}

/** Abre el diálogo nativo y devuelve la fuente, o `null` si el usuario cancela. */
export async function acquireFromDialog(): Promise<ImageSource | null> {
  const path = await window.designfabric.openImageDialog()
  if (!path) return null
  const previewUrl = await window.designfabric.getImagePreview(path)
  return { path, previewUrl, origin: 'dialog' }
}

/**
 * Toma el primer archivo de imagen de un `DataTransfer` (portapapeles o drop),
 * lo materializa en un temporal y devuelve la fuente. `null` si no hay imagen o
 * si la validación (mime aquí, magic bytes en el proceso main) la rechaza — en
 * ese caso, por diseño, "no pasa nada".
 */
export async function acquireFromDataTransfer(
  data: DataTransfer | null,
  origin: 'clipboard' | 'drop'
): Promise<ImageSource | null> {
  if (!data) return null
  const file = Array.from(data.files).find((item) => item.type.startsWith('image/'))
  if (!file) return null

  const bytes = await file.arrayBuffer()
  const written = await window.designfabric.writeTempImage(bytes)
  if (!written) return null
  return { path: written.path, previewUrl: written.previewUrl, origin }
}
