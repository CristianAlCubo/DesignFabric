## Context

Ver `proposal.md` — Why para la motivación. Estado actual relevante:

- El único componente compartido es el visor `core/components/TransparentImage.tsx` (zoom/pan vía
  `useImageViewport`), que acepta un slot `actions`. El resto —botón "Seleccionar", `path-hint`,
  `selectInputImage()`, `exportOutput()`, `waitForJob()`, generadores de nombre— está duplicado inline
  en cada panel y en cada `store.ts` (remove-background, scale, halftone, image-convert).
- **Restricción dura**: el backend Python procesa `input_path` (una ruta en disco), no data URLs ni
  bytes. Hoy la única forma de obtener una entrada es `window.designfabric.openImageDialog()`, que
  devuelve una ruta. El portapapeles y el drag&drop entregan **bytes / `File`**, sin ruta.
- IPC existente relevante (`main/index.ts`): `dialog:openImage` (ruta), `image:preview`
  (ruta → data URL, porque el CSP del renderer bloquea `file://`), `image:export`
  (URL del backend → guardar con diálogo nativo). No existe ningún canal bytes→archivo.
- La IA (sticker) genera desde texto: no tiene entrada de imagen. Sus vistas de resultado
  (`SingleImageResult`, `ResultsGallery`) usan `<img>` crudos, no el visor.

## Goals / Non-Goals

**Goals:**

- Un modelo `ImageSource` único (`{ path, previewUrl, origin }`) que abstraiga de dónde vino la imagen.
- Concentrar los tres orígenes de entrada (diálogo, portapapeles, drag&drop) en `ImageInputZone` +
  `useImageSource`, para que una nueva feature transversal no toque cada pantalla.
- Un IPC nuevo `image:writeTemp` que valide formato y materialice bytes en archivo temporal, con
  registro y limpieza de temporales.
- Un solo camino de exportación (`useImageExport` + `ImageResultView`).
- Generalizar `sendToScale` a un bus de transferencia origen→destino agnóstico.
- Unificar el lado **salida** de la IA bajo la vista de resultado común.

**Non-Goals:**

- No se tocan las entradas de **lista** múltiple (multi-export, clearcut-batch): siguen con su lista de
  rutas y no adoptan `ImageInputZone`.
- No se añade entrada de imagen a la IA (genera desde texto).
- No hay historial/recientes de imágenes (no seleccionado por el usuario).
- No cambia el contrato del backend Python.

## Decisions

### 1. Materializar bytes → archivo temporal en el proceso main (IPC `image:writeTemp`)

Como el backend exige una ruta, portapapeles y drop deben persistir a disco. Se añade
`image:writeTemp(bytes, declaredMime?) → { path, previewUrl } | null`:

- Valida que los bytes sean una imagen soportada (PNG/JPEG/WEBP) **por sniffing de magic bytes**, no
  por la extensión ni el mime declarado (el portapapeles miente/omite). Si no es imagen soportada,
  devuelve `null` — la UI no hace nada (requisito de validación silenciosa).
- Escribe en un subdirectorio temporal propio de la app (bajo `app.getPath('temp')`), devuelve la ruta
  y su data URL de preview (mismo tratamiento que `image:preview`).
- Registra la ruta en un **registro de temporales** en memoria del proceso main.

*Alternativas descartadas*: (a) enviar data URL al backend y cambiar el contrato Python — mayor blast
radius y rompe los CLIs; (b) validar solo por extensión — el portapapeles no trae nombre fiable.

### 2. Ciclo de vida: un temporal por input, propiedad del renderer, borrado en main

`useImageSource` (por instancia de `ImageInputZone`) recuerda la ruta temporal vigente del input. Al
adquirir una entrada nueva (pegar, soltar, o elegir por diálogo/enviar-entre-tabs) invoca
`image:disposeTemp(prevPath)` antes/al registrar la nueva, garantizando **≤1 temporal por input**.

El proceso main mantiene el registro autoritativo y, en el evento `will-quit`/`before-quit`, borra
**todo** temporal aún registrado (red de seguridad ante inputs que no limpiaron). `disposeTemp` de una
ruta no-temporal (proveniente del diálogo nativo o de otra tab) es no-op: solo se borran rutas que el
registro reconoce como temporales creadas por `writeTemp`.

*Alternativa descartada*: borrar por TTL/scheduler — innecesariamente complejo para el requisito
("uno por input + limpieza al cerrar").

### 3. Árbol de componentes en `core/imaging/`

```
core/imaging/
├── ImageViewer         (ex-TransparentImage; visor puro zoom/pan)
├── ImageInputZone      (botón + path-hint + ImageViewer + onPaste/onDrop; usa useImageSource)
├── ImageResultView     (ImageViewer + slot acciones + export; usa useImageExport)
└── StickerResultView   (lado salida IA reusando la base común)
hooks: useImageSource(), useImageExport()
state: imageTransferBus (generaliza sendToScale sobre navigationStore)
```

Cada `store.ts` de feature borra `selectInputImage`/`exportOutput`/`waitForJob` duplicados y consume
los hooks. `waitForJob` duplicado se extrae a un helper compartido en `core/api/`.

*Decisión de herencia*: composición sobre herencia de clases — `ImageResultView` es la base y
`StickerResultView` la **compone/parametriza** (grid + Dialog), en línea con el patrón de slots ya
usado por `TransparentImage.actions`.

### 4. Captura de Ctrl+V con foco por-zona

`ImageInputZone` escucha `paste` cuando está "activa" (foco dentro de la zona o la zona es la única con
entrada visible en la pantalla), evitando que dos zonas de una misma pantalla (entrada vs. resultado)
compitan por el mismo Ctrl+V. El pegado apunta siempre a la **zona de entrada**, no a la de resultado.

### 5. `imageTransferBus` sobre el `navigationStore` existente

`navigationStore` ya permite `setActiveTab` programático (lo usa `sendToScale`). El bus añade una
transferencia pendiente `{ targetTabId, source: ImageSource }` que la pantalla destino consume al
montar/activarse para precargar su input, en vez de que el origen importe el store del destino
directamente (como hace hoy `sendToScale` con `useScaleStore`).

## Risks / Trade-offs

- **Fuga de temporales si el proceso main crashea sin `will-quit`** → Mitigación: al arrancar, limpiar
  el subdirectorio temporal propio de la app (barrido de arranque además del de cierre).
- **Falsos negativos de validación por sniffing** (una imagen válida en formato no soportado, p. ej.
  BMP/GIF) → Mitigación: el conjunto soportado (PNG/JPEG/WEBP) coincide con lo que ya aceptan los
  diálogos y el backend; "no pasa nada" es el comportamiento acordado.
- **Conflictos de Ctrl+V** entre zonas o con inputs de texto de la pantalla → Mitigación: el pegado
  solo se captura cuando el foco no está en un control de texto y se dirige a la zona de entrada activa.
- **Refactor amplio** (toca 4 stores + 4 paneles + IA + IPC) → Mitigación: `ImageViewer` conserva la
  API de `TransparentImage`, permitiendo migrar pantalla por pantalla; el bus mantiene `sendToScale`
  funcionando durante la transición.

## Migration Plan

1. Introducir `image:writeTemp`/`image:disposeTemp` + registro y limpieza en main (sin consumidores).
2. Crear `core/imaging/` con `ImageViewer` (alias de `TransparentImage`) y `useImageSource`/`useImageExport`.
3. Migrar una pantalla piloto (remove-background) a `ImageInputZone` + `ImageResultView`, validar
   diálogo/paste/drop/export.
4. Migrar scale, halftone, image-convert; extraer `waitForJob` compartido; eliminar duplicados.
5. Generalizar `sendToScale` → `imageTransferBus`; migrar la IA al `ImageResultView`/`StickerResultView`.
6. Eliminar `TransparentImage` una vez sin referencias.

Rollback: cada paso es aislable; mientras `ImageViewer` mantenga la firma previa, revertir una pantalla
no afecta a las demás.
