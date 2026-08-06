import { CircleDotDashed } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { HalftonePanel } from './HalftonePanel'

featureRegistry.register({
  id: 'halftone',
  label: 'Semitonos',
  order: 2,
  sectionId: 'retouch',
  icon: CircleDotDashed,
  Panel: HalftonePanel
})
