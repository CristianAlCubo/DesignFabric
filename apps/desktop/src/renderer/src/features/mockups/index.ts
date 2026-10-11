import { Shirt } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { MockupPanel } from './MockupPanel'

featureRegistry.register({
  id: 'mockups',
  label: 'Mockups',
  order: 3,
  sectionId: 'retouch',
  icon: Shirt,
  Panel: MockupPanel
})
