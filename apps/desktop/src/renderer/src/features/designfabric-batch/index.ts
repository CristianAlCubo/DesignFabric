import { LayoutGrid } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { BatchGeneratorView } from './BatchGeneratorView'

featureRegistry.register({
  id: 'designfabric-batch',
  label: 'Generación por lotes (IA)',
  order: 1,
  sectionId: 'create',
  icon: LayoutGrid,
  Panel: BatchGeneratorView
})
