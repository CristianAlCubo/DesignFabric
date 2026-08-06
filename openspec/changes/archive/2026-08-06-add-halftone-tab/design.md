## Context

El algoritmo de halftone existe hoy en un HuggingFace Space (`halftone-converter`) construido con Gradio. Su núcleo (`make_halftone_single` + 4 helpers: `_apply_levels`, `_auto_crop_black`, `_make_halftone_pattern`, y el propio orquestador) es PIL/numpy puro y **no depende de Gradio** — Gradio solo aparece en la capa de UI (`gradio_halftone` + `gr.Blocks`). Las dependencias del core (`pillow`, `numpy`) ya están presentes en el backend de DesignFabric (usadas por ClearCut), por lo que la integración no agrega dependencias.

DesignFabric ya tiene un patrón consolidado para tools CPU single-image: el Feature Registry (`api/registry.py`), con routers como `convert.py`/`scale.py` que encolan jobs asíncronos con afinidad de CPU, reportan progreso por WebSocket y sirven la salida por el mount `/output`. El frontend refleja ese patrón con features autoregistradas en `features/<feature>/`.

La decisión de producto (ya tomada con el usuario): **single-image**, **upload manual**, **preview en vivo baja-res + export full-res**, **resolución/DPI fijos 4500×5400 @300** (idénticos al Gradio).

## Goals / Non-Goals

**Goals:**
- Extraer el core del Space *verbatim* para garantizar salida pixel-idéntica al original, con atribución.
- Exponer las 10 opciones del Gradio con rangos/pasos/defaults idénticos, en UI nativa de DesignFabric.
- Integrarse sin fricción en el patrón de Feature Registry / jobs CPU existente.
- Ofrecer iteración rápida vía preview de baja resolución representativa del resultado final.

**Non-Goals:**
- Batch / procesamiento múltiple (fuera de alcance por ahora).
- Encadenar la entrada desde otras tabs (solo upload manual).
- Exponer resolución/DPI como controles (quedan fijos como en el Gradio).
- Cambiar el algoritmo o "mejorarlo" — se copia tal cual.
- Requerir GPU o el grupo de dependencias `local-ai`.

## Decisions

### 1. Copiar el core verbatim a `core/imaging/halftone_pipeline.py`
Se copian las 4 funciones helper + `make_halftone_single` sin modificaciones algorítmicas, con un docstring/comentario de atribución al Space de origen. Se descarta toda la capa Gradio.
- **Por qué**: garantiza salida pixel-idéntica y minimiza el riesgo de introducir bugs al "portar". Cualquier refactor se hace después, con tests de regresión que fijen la salida actual.
- **Alternativa descartada**: reescribir/limpiar el algoritmo al integrarlo → riesgo de divergencia visual sutil, sin beneficio inmediato.

### 2. Feature CPU siguiendo la plantilla de `convert.py`
Nuevo `JobType.HALFTONE`, `api/routers/halftone.py` con `router` + `build_handlers`, entrada en `_cpu_modules` de `registry.py`, `HalftoneJobRequest` en `schemas.py`. El handler escribe un PNG en `settings.output_dir / "halftone"` y devuelve `{"output_path": ...}` / `image_url`, como `convert`.
- **Por qué**: cero lógica feature-específica en `app.py`/`worker.py`; consistencia con las tabs existentes; el pool CPU ya paraleliza bien este tipo de trabajo.

### 3. Preview vía endpoint síncrono de baja resolución (no job)
El export full-res va como job asíncrono (puede tardar segundos a 4500×5400). La **preview** se sirve por un endpoint dedicado que renderiza a resolución reducida y responde directo (sin cola), suficientemente rápido para iterar. La preview reutiliza el mismo core, ajustando `target_pixels` a la caja reducida.
- **Por qué**: la latencia de la cola + WebSocket es innecesaria para un thumbnail; un request→response simple da mejor sensación de "en vivo". El frontend hace debounce de los cambios de control.
- **Alternativa descartada**: preview como job → overhead de cola/progreso por cada movimiento de slider.

### 4. LPI escalado proporcionalmente en la preview
Como `px_per_cycle = dpi / frequency`, un LPI fijo sobre una imagen más chica produce puntos relativamente más gruesos. La preview escala el LPI efectivo por la razón (resolución_preview / resolución_export) para que el grosor relativo del punto coincida con el del export.
- **Por qué**: hace la preview *representativa* del resultado final sin renderizar a full-res.
- **Trade-off**: el método `diffusion` (Floyd–Steinberg) no escala linealmente, así que su preview es aproximada; se comunica en la UI.

### 5. UI: atenuar controles de trama cuando el método es `diffusion`
Frecuencia, ángulo y forma se deshabilitan/atenúan cuando el método es `diffusion`, ya que el core los ignora en ese caso.
- **Por qué**: evita configurar parámetros sin efecto (mejora sobre el Gradio, que los muestra siempre activos). No cambia el resultado.

## Risks / Trade-offs

- **Preview no 100% idéntica al export** (especialmente `diffusion`) → Mitigación: escalar LPI proporcionalmente para `halftone` y avisar en la UI que el export full-res es el render definitivo.
- **Costo de memoria/CPU del render full-res** (~24 MP, varios arrays float64 en `_make_halftone_pattern`) → Mitigación: corre en el pool CPU como job asíncrono con progreso; no bloquea la UI. La preview reduce el costo durante la iteración.
- **Deriva algorítmica al integrar** → Mitigación: copiar verbatim + test de regresión que fije la salida sobre una imagen de referencia (hash/píxeles).
- **Atribución/licencia del Space de terceros** → Mitigación: conservar nota de atribución en el módulo core; verificar la licencia del Space antes de mergear.

## Migration Plan

Es una feature aditiva: nueva tab, nuevo `JobType`, nuevo router y core. No modifica capabilities existentes ni el esquema de datos. Rollback = quitar la entrada del registry (backend) y del feature registry (frontend); no hay migración de datos ni cambios incompatibles.

## Open Questions

- Resolución exacta de la preview (p. ej. caja ~900×1080, ~1/5 del full-res): elegir el punto que equilibre nitidez del punto vs. latencia; ajustable en implementación.
- Verificación puntual de la licencia del Space `halftone-converter` para dejar la atribución correcta.
