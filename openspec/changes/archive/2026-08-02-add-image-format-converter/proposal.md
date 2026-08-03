## Why

DesignFabric agrupa herramientas de imagen (recorte, escalado, exportación multi-tamaño), pero no permite algo tan básico y pedido como **convertir el formato de un archivo** (p. ej. PNG → JPEG para reducir peso, o cualquier cosa → WEBP para la web). Hoy el usuario tiene que salir del app y usar otra herramienta. Pillow ya es dependencia del backend, así que la capacidad está a un módulo de distancia.

## What Changes

- Se introduce una **nueva sección "Utilidades"** en el sidebar (junto a Generación, Retocado, Lotes), pensada como hogar de herramientas auxiliares de imagen.
- Dentro de Utilidades, un **tab "Conversión de imágenes"** con un segmented control de dos modos independientes:
  - **Individual**: convierte una imagen de un formato a otro; salida servida por `/output` con opción de revelar-en-carpeta (patrón `scale`).
  - **Lote**: convierte N imágenes de cualquier formato a un único formato destino y las empaqueta en un `.zip` (patrón `multi-export`).
- Formatos soportados en v1: **JPEG, JPG, PNG, WEBP**. `JPG` es el codec JPEG con extensión `.jpg` (3 codecs reales, 4 opciones visibles).
- **Slider de calidad** 0–100 para JPEG/WEBP (+ opción WEBP lossless); PNG se guarda optimizado.
- Al convertir una imagen con **transparencia (PNG/WEBP) a JPEG**, el alpha se **aplana sobre blanco** antes de guardar (JPEG no soporta canal alpha).
- Motor de conversión nuevo basado en **Pillow** en `core/imaging/`, expuesto como job **CPU-affinity** (paraleliza en el pool, no toca el worker GPU ni el grupo `local-ai`).

## Capabilities

### New Capabilities
- `image-conversion`: Convertir una imagen individual entre formatos (JPEG/JPG/PNG/WEBP) con control de calidad y aplanado de transparencia sobre blanco para JPEG.
- `image-conversion-batch`: Convertir un lote de imágenes de formatos mixtos a un único formato destino y empaquetar el resultado en un `.zip`.

### Modified Capabilities
<!-- Ninguna: no hay specs existentes cuyos requisitos cambien. La sección "Utilidades" del sidebar es infraestructura de UI que habilita las nuevas capabilities, no una capability con requisitos propios. -->

## Impact

- **Backend (nuevo):**
  - `core/imaging/convert_pipeline.py` — motor Pillow (`convert_one`, `convert_batch`).
  - `api/routers/convert.py` — router `/api/utilities/convert` (+ handlers CPU).
  - `jobs/models.py` — `JobType.CONVERT`.
  - `api/schemas.py` — request/result schemas de conversión (individual y lote).
  - `api/serializers.py` — rama de serialización para `JobType.CONVERT`.
  - `api/registry.py` — una entrada `FeatureModule` (afinidad `cpu`).
- **Frontend (nuevo):**
  - `core/registry/types.ts` y `core/registry/sections.ts` — nuevo `SectionId` `'utilities'` + entrada `SECTIONS` con icono Lucide.
  - `features/image-convert/` — `index.ts` (auto-registro), `ImageConvertPanel.tsx` (toggle de modo), `store.ts` (Zustand), reutilizando `useJobProgress` y el diálogo nativo de selección de archivos.
  - `features/index.ts` — una línea de reexport.
- **Dependencias:** ninguna nueva (Pillow ≥12.3.0 ya presente).
- **Tests:** `backend/tests/core/imaging/` (round-trips de formato, alpha→JPEG, calidad) y `backend/tests/api/` (endpoints, siguiendo `test_multi_export`).
