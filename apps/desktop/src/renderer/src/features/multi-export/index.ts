import { ImagePlus } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { MultiExportPanel } from './MultiExportPanel'

featureRegistry.register({
  id: 'multi-export',
  label: 'Multi-tamaño',
  order: 1,
  sectionId: 'batch-export',
  icon: ImagePlus,
  Panel: MultiExportPanel
})
