// Punto único de descubrimiento de features: cada import de abajo ejecuta el
// side-effect de `featureRegistry.register(...)` dentro del `index.ts` de esa
// feature. Agregar una tool nueva es añadir una carpeta en `features/` con su
// propio `index.ts` y una línea de reexport aquí — no hay switch/if-else que
// tocar en `App.tsx` ni en `AppSidebar`.
import "./remove-background";
import "./scale";
import "./halftone";
import "./clearcut-batch";
import "./multi-export";
import "./image-convert";
import "./designfabric-batch";
import "./designfabric-single";
