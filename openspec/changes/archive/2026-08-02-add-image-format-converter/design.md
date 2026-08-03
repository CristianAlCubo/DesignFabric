## Context

DesignFabric es un monorepo Electron + FastAPI donde cada herramienta es una tab que se auto-registra en un Feature Registry a ambos lados (backend `api/registry.py`, frontend `core/registry/featureRegistry.ts`). El trabajo pesado corre como job asíncrono en pools de workers separados por afinidad GPU/CPU. Esta feature —conversión de formatos con Pillow— es puramente CPU y no requiere el grupo opcional `local-ai`.

Los análogos directos ya existen y se seguirán como molde:
- **`scale`** — job de imagen individual (CPU): router `scale.py`, escribe a `output_dir/scale/<uuid>.png`, devuelve `image_url` vía mount `/output`.
- **`multi-export`** — job de lote → zip (CPU): pipeline `multi_export_pipeline.py` con `reporter`, router `multi_export.py`, resultado con `zip_url`, `expected`/`produced` e ítems por combinación.

El sidebar ya tiene un concepto de **secciones** (`SectionId = 'generation' | 'retouch' | 'batches'` en `core/registry/types.ts`, definidas en `core/registry/sections.ts`); "Utilidades" es simplemente una sección más.

Pillow (`pillow>=12.3.0`) ya es dependencia base — no se agrega nada.

## Goals / Non-Goals

**Goals:**
- Nueva sección "Utilidades" en el sidebar y un tab "Conversión de imágenes" con dos modos (Individual / Lote) mediante segmented control dentro de un mismo tab.
- Convertir entre JPEG/JPG/PNG/WEBP con Pillow, con slider de calidad (JPEG/WEBP), WEBP lossless y PNG optimizado.
- Aplanar transparencia sobre blanco al ir a JPEG.
- Lote de formatos mixtos → un formato destino → `.zip`, con reporte por ítem y continuación ante fallos.
- Reutilizar toda la infraestructura de jobs, progreso WebSocket, mount `/output` y revelado en carpeta ya existente.

**Non-Goals:**
- Formatos más allá de los cuatro pedidos (TIFF, GIF, AVIF, HEIC, etc.) — extensibles después.
- Redimensionado/recorte/optimización avanzada (eso ya lo cubren `scale` y `multi-export`).
- Preservación de EXIF/metadatos e ICC color profiles en v1 (se documenta como riesgo).
- Color de fondo configurable para el aplanado (fijo en blanco por decisión de producto).
- Reutilización de un `output_dir` elegido por el usuario para el lote (se usa el `output_dir` estándar como `scale`/`multi-export`).

## Decisions

### Un solo tab con toggle de modo, no dos tabs
Producto decidió un único tab "Conversión de imágenes" con segmented control `Individual | Lote`. El estado de cada modo vive en un store Zustand (patrón `multi-export/store.ts`). *Alternativa descartada:* dos tabs separados (como `scale` vs `multi-export`) — coherente con el precedente pero el usuario pidió explícitamente un solo tab con dos modos, y reduce ruido en el sidebar.

### Un `JobType.CONVERT` que cubre individual y lote
Ambos modos comparten codec y reglas (calidad, alpha→JPEG); un solo `JobType` con dos endpoints/handlers mantiene la lógica de conversión en un único módulo. La forma del resultado difiere (imagen individual vs zip), así que el request/response distingue el modo. *Alternativa descartada:* dos `JobType` distintos — más entradas en el registry y duplicación del serializer sin beneficio, ya que la afinidad y el pipeline son los mismos.

Estructura de request propuesta:
- `POST /api/utilities/convert` → `{ input_path, target_format, quality, webp_lossless }` → resultado con `output_path`/`image_url`.
- `POST /api/utilities/convert-batch` → `{ image_paths[], target_format, quality, webp_lossless, output_name? }` → resultado con `zip_path`/`zip_url`, `expected`/`produced`, `items[]`.

### Motor Pillow aislado en `core/imaging/convert_pipeline.py`
Funciones de dominio framework-agnósticas (`convert_one`, `convert_batch`) que no conocen FastAPI ni jobs — el router inyecta el `reporter`. Esto respeta la separación `core/` (dominio) vs `api/` (HTTP) y permite testear el codec directamente. `convert_batch` reutiliza el mismo enfoque de empaquetado ZIP que `multi_export_pipeline` (escribir a zip con nombres únicos, reportar por ítem, continuar ante fallo).

### Mapeo de formato → codec/extensión
`JPG` y `JPEG` → codec Pillow `"JPEG"`; extensión `.jpg` para `JPG`, `.jpeg`/`.jpg` para `JPEG` (se estandariza en `.jpg`). `PNG` → `"PNG"` con `optimize=True`. `WEBP` → `"WEBP"` con `quality=` o `lossless=True`. Un pequeño mapa `TargetFormat -> (pillow_format, extension, save_kwargs_builder)` centraliza esto.

### Aplanado sobre blanco solo cuando aplica
Antes de guardar a JPEG: si `img.mode in ("RGBA","LA","P"con transparencia)`, componer sobre `Image.new("RGB", size, (255,255,255))` con `alpha_composite`/`paste(mask)`; si no, convertir a `RGB` directo. Nunca alterar fondo en PNG/WEBP destino.

### Sección "Utilidades" como infraestructura de UI
Añadir `'utilities'` al union `SectionId`, una entrada a `SECTIONS` con icono Lucide (p. ej. `Wrench`), y la feature se enchufa vía `sectionId: 'utilities'`. No es una capability con requisitos propios; solo habilita las dos capabilities de conversión.

## Risks / Trade-offs

- **Pérdida silenciosa de EXIF/ICC al convertir** → v1 no preserva metadatos ni perfiles de color; documentarlo en la UI/notas y dejar como mejora futura (Pillow puede pasar `exif=`/`icc_profile=` más adelante).
- **Aplanado a blanco no deseado para algunos usuarios** → decisión de producto fija en v1; el diseño aísla el color de relleno en un solo punto para hacerlo configurable después sin refactor.
- **Colisión de nombres en el lote** (dos entradas → mismo nombre) → resolver con sufijo/índice único dentro del ZIP, cubierto por escenario de spec.
- **Archivo de entrada corrupto o formato no soportado** → `convert_one` captura y reporta el fallo por ítem; el lote continúa (escenario de spec). El individual devuelve error de job.
- **WEBP lossless + slider de calidad ambiguo** → cuando `webp_lossless` está activo se ignora `quality` (escenario de spec explícito) para evitar expectativas confusas.

## Migration Plan

Feature puramente aditiva, sin migración de datos ni breaking changes:
1. Backend: `JobType.CONVERT`, `convert_pipeline.py`, `convert.py` router, schemas, serializer, entrada en `FEATURE_REGISTRY` (cpu).
2. Frontend: `SectionId`/`SECTIONS`, carpeta `features/image-convert/` con auto-registro, línea en `features/index.ts`.
3. Tests backend (core + api) siguiendo `test_multi_export`.
Rollback = revertir el commit; nada persistente que deshacer.

## Open Questions

- Ninguna bloqueante. Confirmado con el usuario: un tab con toggle, aplanado sobre blanco, slider de calidad + WEBP lossless. Supuestos aceptados: lote a un único formato destino conservando nombres base; salida al `output_dir` estándar.
