import { featureRegistry } from '../../core/registry/featureRegistry'
import { ScalePanel } from './ScalePanel'

featureRegistry.register({
  id: 'scale',
  label: 'Escalado',
  order: 1,
  sectionId: 'retouch',
  Panel: ScalePanel
})
