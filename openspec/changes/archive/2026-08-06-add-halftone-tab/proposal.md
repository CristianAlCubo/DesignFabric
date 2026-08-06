## Why

Los usuarios que preparan diseños para print-on-demand / serigrafía necesitan convertir una imagen a su versión con semitonos (halftone). Hoy esa capacidad vive fuera de DesignFabric, en un HuggingFace Space basado en Gradio (`halftone-converter`), lo que obliga a salir de la app y no se integra con el resto del flujo (quitar fondo, escalar, exportar). El core del algoritmo es PIL/numpy puro y no depende de Gradio, por lo que puede extraerse e integrarse como una tab nativa más, reutilizando el patrón de features CPU ya existente.

## What Changes

- Nueva tab **"Halftone"** dentro de la sección "Utilidades", con UI propia de DesignFabric (no se embebe Gradio).
- Se extrae el core del Space `halftone-converter` (`make_halftone_single` + 4 helpers) *verbatim* a un módulo de dominio, garantizando salida pixel-idéntica al original, con nota de atribución.
- La tab replica **1:1** las 10 opciones que expone el Gradio original, con rangos/pasos/defaults idénticos: crop de fondo negro (checkbox + umbral 0–255), niveles (black point 0–255, white point 0–255, gamma 0.1–3.0), invertir para prenda oscura (checkbox), método (`halftone`/`diffusion`), frecuencia de trama LPI (5–100), ángulo de trama (0–90°), y forma del punto (`round`/`line`).
- **Single-image** únicamente; entrada por **upload manual**.
- **Preview en vivo** a resolución reducida (con LPI escalado proporcionalmente para que el punto sea representativo del resultado final) + **export a resolución completa** bajo demanda.
- Resolución de salida y DPI **fijos en 4500×5400 @300** (hardcodeados igual que en el Gradio; no se exponen como controles).
- Los controles específicos de trama (frecuencia, ángulo, forma) se **atenúan/deshabilitan** cuando el método es `diffusion`, dado que no aplican (mejora de UX sobre el Gradio, sin cambiar el resultado).
- La salida es un **PNG RGBA transparente** que conserva los colores originales (el halftone va en el canal alpha).
- Se ejecuta como **job asíncrono con afinidad de CPU**, siguiendo el patrón de `convert`/`scale`.

## Capabilities

### New Capabilities
- `halftone-conversion`: convertir una imagen individual a su versión con semitonos, con todas las opciones de crop, niveles, inversión, método (dot screen o difusión de error), frecuencia/ángulo/forma de trama; export a PNG RGBA transparente a resolución completa como job CPU asíncrono.
- `halftone-preview`: generar una previsualización rápida a resolución reducida con LPI escalado proporcionalmente, para iterar sobre los parámetros sin pagar el costo del render full-res.

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos. -->

## Impact

- **Backend nuevo**:
  - `core/imaging/halftone_pipeline.py` (core extraído del Space + atribución).
  - `api/routers/halftone.py` (endpoint de export como job + endpoint de preview).
  - `jobs/models.py`: nuevo `JobType.HALFTONE`.
  - `api/schemas.py`: `HalftoneJobRequest` (+ schema de preview).
  - `api/registry.py`: nueva entrada en `_cpu_modules` (afinidad CPU).
  - Tests en `tests/core/imaging/` y `tests/api/`.
- **Frontend nuevo**:
  - `apps/desktop/src/renderer/src/features/halftone/` (tab autoregistrada + `TabDescriptor`), con los 10 controles, tooltips en español, atenuado condicional por método, panel de preview en vivo + botón de export.
  - Registro de `JobType.HALFTONE` en el lado frontend.
- **Dependencias**: ninguna nueva — `pillow` y `numpy` ya son dependencias del backend (ClearCut). No requiere el grupo `local-ai` ni GPU.
- **Atribución/licencia**: se conserva referencia al Space `halftone-converter` de origen en el módulo core.
