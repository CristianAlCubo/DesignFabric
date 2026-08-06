## 1. Core de dominio (backend)

- [x] 1.1 Crear `core/imaging/halftone_pipeline.py` copiando *verbatim* del Space los helpers `_apply_levels`, `_auto_crop_black`, `_make_halftone_pattern` y `make_halftone_single`, sin cambios algorítmicos.
- [x] 1.2 Añadir docstring/comentario de atribución al Space `halftone-converter` y verificar su licencia. (El Space no declara licencia — sin campo `license:` ni archivo LICENSE; atribución añadida en el docstring; pendiente confirmar licencia con el autor.)
- [x] 1.3 Exponer una función de conveniencia para preview que renderice a una caja reducida con LPI escalado proporcionalmente (razón resolución_preview/full-res), reutilizando el mismo core.
- [x] 1.4 Test de regresión que fije la salida sobre una imagen de referencia para método `halftone` y `diffusion` (hash o comparación de píxeles), incluyendo casos de crop on/off e invert on/off.

## 2. Capa de jobs y API (backend)

- [x] 2.1 Agregar `JobType.HALFTONE` en `jobs/models.py`.
- [x] 2.2 Definir `HalftoneJobRequest` (y schema de preview) en `api/schemas.py` con los 10 parámetros, rangos/defaults idénticos al Gradio (crop bg + umbral, black/white point, gamma, invert, método, LPI, ángulo, forma).
- [x] 2.3 Crear `api/routers/halftone.py` con `router` (prefijo `/api/utilities`), endpoint de export como job (`POST /halftone`) y `build_handlers` que escribe el PNG RGBA en `output_dir/halftone` y devuelve `output_path`/`image_url`.
- [x] 2.4 Añadir endpoint de preview síncrono (baja resolución, sin cola) que devuelve la imagen o su URL directamente.
- [x] 2.5 Registrar la feature en `_cpu_modules` de `api/registry.py` (afinidad CPU, `JobType.HALFTONE`).
- [x] 2.6 Tests de API: creación del job de export (202 + job_id), salida PNG con alpha y DPI 300, y respuesta del endpoint de preview.

## 3. Frontend — feature tab

- [x] 3.1 Crear `apps/desktop/src/renderer/src/features/halftone/` con su `index.ts` autoregistrando el `TabDescriptor` (sección "Retocar", junto a Eliminación de fondo y Escalado).
- [x] 3.2 Registrar la feature en el lado frontend (tipos + cliente API para export y preview vía store Zustand).
- [x] 3.3 Construir la UI con los 10 controles (checkbox/slider/toggle) usando rangos, pasos y defaults exactos de la tabla del Gradio, con tooltips en español portados de los `info=` del original.
- [x] 3.4 Componente de upload manual de la imagen de entrada; estado de "falta imagen" que impide el export.
- [x] 3.5 Atenuar/deshabilitar Frecuencia LPI, Ángulo y Forma cuando el método es `diffusion`.
- [x] 3.6 Panel de preview en vivo (baja res) con debounce de cambios de control, y botón "Exportar full-res" para el render vía job.
- [x] 3.7 Aviso en la UI de que el export full-res es el render definitivo y que `diffusion` puede diferir de la preview.

## 4. Verificación e integración

- [x] 4.1 `uv run ruff check .` + `uv run mypy src` en backend sin errores nuevos. (Los archivos de halftone pasan limpios; los únicos hallazgos son pre-existentes y ajenos al cambio: `jobs/worker.py` import `Job` sin usar, y errores de `local-ai`/serializers previos.)
- [x] 4.2 `npm run typecheck` en frontend sin errores.
- [x] 4.3 `uv run pytest -m "not integration"` verde (282 passed).
- [ ] 4.4 Prueba manual en `npm run dev`: subir imagen, iterar con preview, exportar y validar el PNG RGBA a 4500×5400 @300. (Pendiente: requiere levantar el Electron; se deja para validación del usuario.)
