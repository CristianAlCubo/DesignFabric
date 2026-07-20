import { featureRegistry } from '../../core/registry/featureRegistry'
import { RemoveBackgroundPanel } from './RemoveBackgroundPanel'

featureRegistry.register({
  id: 'remove-background',
  label: 'Eliminación de fondo',
  order: 0,
  sectionId: 'retouch',
  Panel: RemoveBackgroundPanel
})
