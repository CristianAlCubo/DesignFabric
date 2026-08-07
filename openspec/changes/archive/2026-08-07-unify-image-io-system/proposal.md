## Why

Cada pantalla de imagen (remove-background, scale, halftone, image-convert) reimplementa
por su cuenta la columna de entrada (botón "Seleccionar" + hint de ruta + visor) y la de
resultado (visor + exportar), tanto en el JSX del panel como en la lógica IPC de su `store.ts`.
El único componente realmente compartido es el visor (`TransparentImage`); todo lo demás es
copy-paste divergente (`selectInputImage`, `exportOutput`, `waitForJob`, nombres de exportación).
Esta duplicación impide añadir features transversales de entrada/salida —pegar del portapapeles,
arrastrar y soltar, exportación unificada, enviar imágenes entre pestañas— sin tocar cada
pantalla una por una. Queremos un árbol de componentes de imagen unificado que concentre esos
comportamientos en un solo lugar.

## What Changes

- **Nueva abstracción "fuente de imagen"**: un modelo único (`ImageSource`: `path`, `previewUrl`,
  `origin`) del que dependen todas las pantallas, en vez de que cada store maneje su propio
  `inputPath`/`inputPreview` a mano.
- **Pegar del portapapeles (Ctrl+V)** en el input de imagen de cualquier pantalla. Como el backend
  procesa rutas de archivo (`input_path`) y el portapapeles entrega bytes, se añade un IPC nuevo que
  materializa esos bytes en un **archivo temporal** y devuelve su ruta.
- **Arrastrar y soltar (drag & drop)** una imagen sobre la zona de entrada, reutilizando el mismo
  mecanismo de archivo temporal.
- **Validación de imagen**: si lo pegado/soltado no es una imagen soportada (PNG/JPEG/WEBP), no
  ocurre nada — no se crea archivo temporal ni se muestra error intrusivo.
- **Ciclo de vida acotado de temporales**: cada input mantiene **como máximo un** archivo temporal
  a la vez; al pegar/soltar uno nuevo se descarta el anterior, y **todos** se eliminan al cerrar la
  app. Sin acumulación ni fugas.
- **Exportación unificada**: un solo camino de exportación (`useImageExport` + vista de resultado
  compartida) que reemplaza las tres implementaciones divergentes de `exportOutput` y sus generadores
  de nombre.
- **Enviar imágenes entre pestañas generalizado**: el actual `sendToScale` (acoplado a un par fijo)
  se generaliza a un mecanismo que lleva el output de cualquier pantalla al input de otra.
- **UI de "Enviar a…" por menú contextual**: el click derecho sobre un `ImageResultView` con resultado
  abre un menú contextual con la opción «Enviar a:», que despliega un submenú anidado con las pantallas
  destino soportadas. Cada instancia de `ImageResultView` declara **por props** a qué pantallas puede
  enviar su resultado (no hay una lista global fija).
- **Árbol de componentes unificado** en `core/imaging/`: `ImageViewer` (base, ex-`TransparentImage`),
  `ImageInputZone` (entrada + los 3 orígenes globales), `ImageResultView` (resultado + export), y las
  vistas de resultado de IA (`SingleImageResult`, `ResultsGallery`) pasan a heredar de la base común.

## Capabilities

### New Capabilities
- `image-input`: adquisición unificada de la imagen de entrada de una pantalla desde diálogo nativo,
  portapapeles (Ctrl+V) o arrastrar-y-soltar, con validación de formato y ciclo de vida acotado del
  archivo temporal (uno por input, descartado al reemplazar o al cerrar la app).
- `image-transfer`: envío del resultado de una pantalla como entrada de otra pestaña, de forma
  genérica entre cualquier par origen→destino.

### Modified Capabilities
<!-- Ninguna: los specs de features existentes (halftone, image-conversion, etc.) no cambian sus
     requisitos de dominio; la nueva forma de aportar la imagen de entrada queda descrita por la
     capability transversal `image-input`. La exportación unificada es refactor de implementación
     (mismo comportamiento observable de guardado), no un cambio de requisito de spec. -->

## Impact

- **Frontend renderer**: nuevo `core/imaging/` (componentes + hooks `useImageSource`, `useImageExport`,
  bus de transferencia). Adelgazan los `store.ts` de remove-background, scale, halftone, image-convert
  (se eliminan `selectInputImage`/`exportOutput`/`waitForJob` duplicados). Paneles migran a los
  componentes compartidos. `TransparentImage` se convierte en/deja paso a `ImageViewer`.
- **Electron main + preload**: nuevo IPC `image:writeTemp(bytes, mime) → path` (con validación de
  formato), registro de temporales y limpieza en el evento de cierre de la app.
- **IA (sticker)**: `SingleImageResult` y `ResultsGallery` pasan a apoyarse en la vista de resultado
  común (lado salida). No aplican los orígenes de entrada (la IA genera desde texto).
- **Sin cambios de backend Python**: sigue recibiendo `input_path`; los temporales son rutas válidas
  en disco.
- **Fuera de alcance**: entradas de *lista* múltiple (multi-export, clearcut-batch) conservan su lista
  de rutas; no adoptan `ImageInputZone` en este cambio.
