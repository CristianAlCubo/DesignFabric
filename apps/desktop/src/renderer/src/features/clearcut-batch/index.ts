import { featureRegistry } from '../../core/registry/featureRegistry'
import { BatchPanel } from './BatchPanel'

featureRegistry.register({
  id: 'clearcut-batch',
  label: 'Lote',
  order: 0,
  sectionId: 'batches',
  Panel: BatchPanel
})
