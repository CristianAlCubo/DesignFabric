## 1. Motor de conversión (core/imaging)

- [x] 1.1 Crear `core/imaging/convert_pipeline.py` con un mapa `TargetFormat -> (pillow_format, extension, save_kwargs)` que cubra JPEG/JPG/PNG/WEBP (JPG y JPEG → codec `"JPEG"`, extensión `.jpg`)
- [x] 1.2 Implementar `convert_one(src, dest, target_format, quality=90, webp_lossless=False)`: decodifica con Pillow, aplana sobre blanco si destino es JPEG y hay alpha, guarda con `quality`/`optimize`/`lossless` según formato
- [x] 1.3 Implementar `convert_batch(paths, target_format, zip_path, quality, webp_lossless, reporter)`: convierte cada imagen a un miembro del ZIP conservando el nombre base, asegura nombres únicos, reporta progreso por ítem y continúa ante fallos, devolviendo un reporte con `expected`/`produced`/`items`
- [x] 1.4 Definir el dataclass de reporte del lote (`to_dict()`) siguiendo el patrón de `multi_export_pipeline`

## 2. Backend — jobs, schemas y router

- [x] 2.1 Añadir `JobType.CONVERT = "convert"` en `jobs/models.py`
- [x] 2.2 Añadir schemas en `api/schemas.py`: `ConvertJobRequest`, `ConvertResultSchema` (individual) y `ConvertBatchJobRequest`, `ConvertBatchItemResultSchema`, `ConvertBatchResultSchema` (lote), con `target_format` restringido a JPEG/JPG/PNG/WEBP y `quality` acotado 0–100
- [x] 2.3 Crear `api/routers/convert.py` con prefix `/api/utilities`: endpoint `POST /convert` (individual) y `POST /convert-batch` (lote), ambos encolando un `Job.new(JobType.CONVERT, payload)`, más `build_handlers(settings, store)` (patrón `scale.py` + `multi_export.py`)
- [x] 2.4 En los handlers, escribir la salida individual en `output_dir/convert/<uuid>.<ext>` y el ZIP del lote en `output_dir/convert/<name>-<uuid>.zip`
- [x] 2.5 Añadir las ramas de serialización para `JobType.CONVERT` en `api/serializers.py` (individual → `image_url`; lote → `zip_url`, `expected`, `produced`, `items`) y ampliar el union de `JobStatusResponse.result`
- [x] 2.6 Registrar la feature en `api/registry.py`: una entrada `FeatureModule("image-convert", convert.router, (JobType.CONVERT,), "cpu", convert.build_handlers)` dentro de `_cpu_modules`

## 3. Frontend — sección Utilidades y registro

- [x] 3.1 Añadir `'utilities'` al union `SectionId` en `core/registry/types.ts`
- [x] 3.2 Añadir la entrada de sección "Utilidades" en `core/registry/sections.ts` con un icono Lucide (p. ej. `Wrench`) y el `order` adecuado
- [x] 3.3 Crear `features/image-convert/index.ts` que registre el `TabDescriptor` (`id: 'image-convert'`, `sectionId: 'utilities'`, label "Conversión de imágenes")
- [x] 3.4 Añadir `import './image-convert'` en `features/index.ts`

## 4. Frontend — panel y estado

- [x] 4.1 Crear `features/image-convert/store.ts` (Zustand) con el estado de ambos modos: modo activo, archivos seleccionados, formato destino, calidad, WEBP lossless y resultado
- [x] 4.2 Crear `features/image-convert/ImageConvertPanel.tsx` con segmented control `Individual | Lote`, selector de formato destino, slider de calidad (deshabilitado para PNG y cuando WEBP lossless está activo) y checkbox WEBP lossless
- [x] 4.3 Modo Individual: selección de un archivo vía diálogo nativo, llamada a `POST /api/utilities/convert`, sondeo del job hasta terminar, y acción de exportar (save-as) sobre `image_url` (patrón `scale`)
- [x] 4.4 Modo Lote: selección múltiple de archivos, llamada a `POST /api/utilities/convert-batch`, progreso vía `useJobProgress`, y descarga/enlace del `zip_url` con resumen `producido/esperado` e ítems fallidos (patrón `multi-export`)

## 5. Tests

- [x] 5.1 `backend/tests/core/imaging/test_convert_pipeline.py`: round-trips de los cuatro formatos, JPG↔JPEG mismo codec, aplanado de alpha→JPEG sobre blanco, calidad afecta peso JPEG, WEBP lossless ignora calidad, PNG optimizado
- [x] 5.2 `backend/tests/core/imaging/`: lote con nombres duplicados (unicidad en ZIP) y con un ítem corrupto (continúa y reporta `expected` vs `produced`)
- [x] 5.3 `backend/tests/api/test_convert.py`: endpoints `POST /api/utilities/convert` y `/convert-batch` devuelven 202 + `job_id`, y el job serializado expone `image_url`/`zip_url` correctamente (siguiendo `test_multi_export`)

## 6. Verificación

- [x] 6.1 Ejecutar `cd backend && uv run pytest -m "not integration"` (215 passed), `uv run ruff check .` y `uv run mypy src` — archivos nuevos/tocados limpios; los únicos hallazgos (`worker.py` F401, `serializers.py` image_url, imports torch/diffusers) son preexistentes en la rama base, ajenos a este cambio
- [x] 6.2 Ejecutar `npm run typecheck` en el frontend (sin errores)
- [ ] 6.3 Prueba manual en `npm run dev`: convertir un PNG con transparencia a JPEG (fondo blanco), y un lote mixto a WEBP descargando el ZIP — pendiente de verificación manual del usuario (requiere GUI)
