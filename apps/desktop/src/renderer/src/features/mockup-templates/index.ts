import { Ruler } from 'lucide-react'

import { featureRegistry } from '../../core/registry/featureRegistry'
import { MockupTemplatePanel } from './MockupTemplatePanel'

featureRegistry.register({
  id: 'mockup-templates',
  label: 'Plantillas de mockup',
  order: 20,
  sectionId: 'batch-export',
  icon: Ruler,
  Panel: MockupTemplatePanel
})
