import { featureRegistry } from '../../core/registry/featureRegistry'
import { SingleImageView } from './SingleImageView'

featureRegistry.register({
  id: 'designfabric-single',
  label: 'Imagen única (prompt libre)',
  order: 0,
  sectionId: 'generation',
  Panel: SingleImageView
})
