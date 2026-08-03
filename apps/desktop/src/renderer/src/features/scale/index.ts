import { Scaling } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { ScalePanel } from './ScalePanel'

featureRegistry.register({
  id: 'scale',
  label: 'Escalado',
  order: 1,
  sectionId: 'retouch',
  icon: Scaling,
  Panel: ScalePanel
})
