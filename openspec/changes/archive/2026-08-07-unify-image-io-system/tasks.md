## 1. IPC de temporales (Electron main + preload)

- [x] 1.1 Añadir handler `image:writeTemp(bytes, declaredMime?)` en `main/index.ts`: validar imagen por magic bytes (PNG/JPEG/WEBP), escribir en subdirectorio temporal propio bajo `app.getPath('temp')`, devolver `{ path, previewUrl }` o `null` si no es imagen soportada
- [x] 1.2 Añadir registro en memoria de rutas temporales creadas y handler `image:disposeTemp(path)` que borra solo rutas del registro (no-op para rutas no registradas)
- [x] 1.3 Barrido de temporales del subdirectorio propio en el arranque de la app y limpieza total en `will-quit`/`before-quit`
- [x] 1.4 Exponer `writeTempImage`/`disposeTempImage` en `preload/index.ts` y sus tipos en `preload/index.d.ts`

## 2. Núcleo compartido (`core/imaging/` + hooks)

- [x] 2.1 Mover `TransparentImage` a `core/imaging/ImageViewer.tsx` conservando su API pública (props y slot `actions`); dejar re-export temporal desde la ruta antigua para migración incremental
- [x] 2.2 Definir el modelo `ImageSource` (`{ path, previewUrl, origin: 'dialog' | 'clipboard' | 'drop' | 'transfer' }`)
- [x] 2.3 Crear `useImageSource()`: unifica selección por diálogo, pegado y drop; gestiona el temporal vigente del input (≤1) llamando a `disposeTempImage` del anterior al adquirir uno nuevo
- [x] 2.4 Crear `useImageExport()`: unifica `exportImage(...)` y consolida los generadores de nombre divergentes en una sola política
- [x] 2.5 Extraer el `waitForJob` duplicado a un helper compartido en `core/api/`

## 3. Componentes de entrada y resultado

- [x] 3.1 Crear `ImageInputZone`: botón "Seleccionar" + `path-hint` + `ImageViewer` + captura de `onPaste`/`onDrop` dirigida a la zona de entrada activa (no a la de resultado ni a inputs de texto)
- [x] 3.2 Crear `ImageResultView`: `ImageViewer` + slot de acciones + exportación vía `useImageExport`
- [x] 3.3 Verificar validación silenciosa: pegar/soltar contenido no-imagen no crea temporal, no cambia la entrada y no muestra error intrusivo

## 4. Transferencia entre pestañas

- [x] 4.1 Crear `imageTransferBus` sobre `navigationStore` con transferencia pendiente `{ targetTabId, source: ImageSource }`
- [x] 4.2 Hacer que `ImageInputZone` consuma la transferencia pendiente de su pestaña al activarse y precargue su entrada
- [x] 4.3 Reescribir `sendToScale` en términos del bus genérico y eliminar el acoplamiento directo a `useScaleStore`

## 5. Migración de pantallas de imagen

- [x] 5.1 Piloto remove-background: migrar panel a `ImageInputZone`/`ImageResultView`; eliminar `selectInputImage`/`exportOutput`/`waitForJob` de su store; validar diálogo/paste/drop/export/enviar-a-escalado
- [x] 5.2 Migrar scale a los componentes/hooks compartidos y limpiar su store
- [x] 5.3 Migrar halftone (entrada por `ImageInputZone`; el preview en vivo sigue en su store) y limpiar duplicados
- [x] 5.4 Migrar image-convert (modo individual) a los componentes/hooks compartidos y limpiar su store

## 6. Unificar lado salida de IA

- [x] 6.1 Refactorizar `SingleImageResult` para apoyarse en `ImageResultView`/`StickerResultView` (base común)
- [x] 6.2 Refactorizar `ResultsGallery` (grid + Dialog) sobre la vista de resultado común

## 7. Limpieza y verificación

- [x] 7.1 Eliminar `TransparentImage` y el re-export temporal una vez sin referencias
- [x] 7.2 `npm run typecheck` + `build:app` OK. Pendiente: prueba manual en la app real de paste/drop/export/transferencia y de que no quedan temporales tras cerrar (no ejecutable en este entorno headless)

## 8. Menú contextual "Enviar a…" en ImageResultView

- [x] 8.1 Añadir componente shadcn `context-menu` (Radix `ContextMenu` con soporte de submenú) en `components/ui/`
- [x] 8.2 `ImageResultView` acepta prop `sendTargets?: string[]` (ids de pestaña) y `sourcePath`; envuelve el visor en un `ContextMenu` que, con resultado presente y targets declarados, muestra «Enviar a:» → submenú con las pantallas (labels resueltos desde `featureRegistry`), que llaman al bus de transferencia
- [x] 8.3 Cablear `sendTargets` en cada panel (remove-background, scale, image-convert) y retirar el botón fijo "Enviar a escalado" de remove-background
- [x] 8.4 `npm run typecheck` + `build:app`
