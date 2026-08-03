import { RefreshCw } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { ImageConvertPanel } from './ImageConvertPanel'

featureRegistry.register({
  id: 'image-convert',
  label: 'Conversión de imágenes',
  order: 2,
  sectionId: 'batch-export',
  icon: RefreshCw,
  Panel: ImageConvertPanel
})
