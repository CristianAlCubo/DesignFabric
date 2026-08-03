import { featureRegistry } from '../../core/registry/featureRegistry'
import { ImageConvertPanel } from './ImageConvertPanel'

featureRegistry.register({
  id: 'image-convert',
  label: 'Conversión de imágenes',
  order: 0,
  sectionId: 'utilities',
  Panel: ImageConvertPanel
})
