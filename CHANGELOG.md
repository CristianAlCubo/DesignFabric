# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Sistema unificado de entrada/salida de imágenes en las pantallas de Retocar/Utilidades: pegar del portapapeles (Ctrl+V) y arrastrar-y-soltar una imagen sobre la zona de entrada de cualquier pantalla (eliminación de fondo, escalado, semitonos, conversión individual), además del diálogo nativo. El contenido pegado/soltado se valida por *magic bytes* (PNG/JPEG/WEBP) — si no es una imagen soportada, no pasa nada — y se materializa en un archivo temporal cuyo ciclo de vida está acotado: cada input mantiene como máximo un temporal (el anterior se descarta al pegar/soltar/elegir otro) y todos se eliminan al cerrar la app, con barrido de arranque como red de seguridad.
- Menú contextual «Enviar a:» (click derecho sobre el resultado) que transfiere el resultado de una pantalla como imagen de entrada de otra pestaña, navegando y precargándola allí. Cada pantalla declara por configuración a qué destinos puede enviar, generalizando el antiguo botón fijo «Enviar a escalado» a cualquier par origen→destino.
- Herramienta «Multi-tamaño» en la sección Lotes: exporta una o varias imágenes contra una lista de tamaños (fijos en píxeles o porcentuales relativos a las dimensiones de cada imagen), generando un archivo por cada combinación imagen×tamaño y empaquetándolos en un `.zip`, con plantillas de nombre por fila (`{name}`/`{width}`/`{height}`/`{percent}`/`{prefix}`), subcarpeta por imagen, progreso por ítem y resiliencia a fallos parciales — usa redimensionado clásico en CPU, sin invocar el escalado por IA. Incluye presets de tamaños reutilizables: crear/editar/duplicar/eliminar, presets de fábrica de solo lectura, y exportación/importación a `.json` con validación.
- Sección «Utilidades» en el sidebar con la herramienta «Conversión de imágenes»: convierte entre JPEG, JPG, PNG y WEBP con Pillow (job asíncrono con afinidad de CPU), en dos modos independientes dentro de un mismo tab — Individual (con previsualización y exportación vía diálogo nativo) y Lote (varias imágenes a un único formato destino, empaquetadas en un `.zip` descargable, resiliente a fallos parciales con reporte por ítem). Incluye control de calidad para JPEG/WEBP, opción WEBP sin pérdida (lossless), PNG optimizado y aplanado de transparencia sobre blanco al convertir a JPEG.
- Herramienta «Semitonos» en la sección Retocar: convierte una imagen a su versión con semitonos (halftone) para print-on-demand / serigrafía, integrando el core del Space `halftone-converter` (PIL + numpy) como backend nativo, sin embeber Gradio. Replica las opciones del original con UI propia — recorte de fondo negro (con umbral), niveles (punto negro/blanco, gamma), inversión para prenda oscura, método de trama de puntos (`halftone`) o difusión de error Floyd–Steinberg (`diffusion`), y frecuencia/ángulo/forma (redondo o línea) de la trama. La salida es un PNG RGBA transparente a 4500×5400 @300 que conserva los colores originales en el canal alpha (job asíncrono con afinidad de CPU). Incluye previsualización en vivo a baja resolución (con la frecuencia de trama escalada proporcionalmente para que el punto sea representativo del resultado) que se regenera con cada ajuste, y guardado que genera el render a resolución completa on-demand.

### Changed

- Rediseño del sidebar principal a un árbol anidado (secciones + herramientas indentadas, siempre expandido) que reemplaza el esquema anterior de sidebar + franja de pestañas horizontal oculta hasta entrar a cada sección. Las 4 secciones (Generación, Retocado, Lotes, Utilidades) se reagruparon en 3 por etapa del flujo — **Crear**, **Retocar**, **Lote y Exportación** — resolviendo que el concepto "lote" estuviera repartido entre dos secciones sin relación y eliminando la sección de una sola herramienta. Cada herramienta ahora muestra su propio icono en el árbol.
- El sidebar es más ancho (15.5rem → 19rem) para que las etiquetas más largas no se corten, la sección que contiene la pestaña activa se resalta (texto e icono en color de acento), y el sidebar ahora es colapsable (botón dedicado en la cabecera de contenido + atajo `Ctrl/Cmd+B`).

## [0.2.0] - 2026-07-20

### Added

- OpenRouter como provider de texto e imagen: API key con cifrado seguro (`safeStorage`), selectores de modelo en Settings, y jobs de generación junto a Ollama/FLUX.2. Usa la API de `/images` para modelos solo-imagen y pide transparencia según las capacidades de cada modelo, con cancelación cooperativa de jobs.
- Ventana hija de Configuración (Settings), con navegación por secciones (OpenRouter, modelos de lenguaje, modelos de imagen, IA local, general).
- Endpoint `GET /api/generation/readiness` como fuente de verdad del estado de generación IA (deps `local-ai`, Ollama reachable/modelos, pesos FLUX en caché HF, CUDA); la UI deshabilita en los selectores los providers no ejecutables.
- Sección "IA local" en Settings para instalar el módulo de generación local (Ollama + FLUX.2 Klein, varios GB) en cualquier momento después del primer arranque, con progreso en vivo.

### Changed

- Rediseño del shell: dashboard con sidebar de dos niveles (Generación, Retocado, Lotes), consola de logs movida a un sheet lateral y cerrada por defecto.
- Migración de la UI a componentes shadcn/Radix con Tailwind 4; botones de producto unificados bajo `AppButton` con iconos Lucide.
- El estado de los formularios de generación (batch/single) se persiste en stores Zustand y ya no se pierde al cambiar de sección o tab.
- Actualización de Electron 36.9.5 → 43.1.1 (Chromium/Node más nuevos; el paquete `electron` ya no autodescarga el binario en `postinstall` desde la v40, `npm run setup` lo cubre explícitamente).

### Fixed

- 404 en modelos OpenRouter solo-imagen por pedir siempre `image+text` modalities; ahora resuelve las modalities por modelo.
- "Failed to fetch" al abrir la UI antes de que el backend esté listo; progreso/ETA y cola del lote ClearCut endurecidos para cientos de archivos.
- Flash de skeleton en Settings > OpenRouter en cargas rápidas de IPC.
- Backend empaquetado (`.AppImage`/`.exe`) crasheaba al arrancar con `ModuleNotFoundError: httpx` — la dependencia estaba declarada solo en el extra de desarrollo.

### Removed

- Wizard de primer arranque que bloqueaba el inicio preguntando si instalar el módulo de IA local; ahora arranca directo (equivalente a elegir "Más tarde") y la instalación se hace desde Settings > IA local sin reiniciar la app.
- Estrategia de escalado vectorial (VTracer + CairoSVG). Real-ESRGAN queda como única opción de escalado en Escalado, Lote, API y CLI.

## [0.1.0] - 2026-07-20

Primer release: fusión de **ClearCut** (eliminación de fondo y escalado/vectorizado de imágenes) y **DesignFabric** (generación de stickers vía Ollama + FLUX.2 Klein) en una sola app de escritorio.

### Added

- App de escritorio Electron con un tabpane unificado (layout de ClearCut) y paleta de colores de DesignFabric, con 5 herramientas: Eliminación de fondo, Escalado, Lote (ClearCut), Generación por lotes (IA) e Imagen única (IA).
- Backend único en FastAPI (`designfabric`) que expone las 5 herramientas vía HTTP + WebSocket, con un sistema de jobs asíncronos con dos pools de ejecución: `GpuJobWorker` (serializado, para Ollama/FLUX.2) y `CpuJobWorker` (paralelo, para ClearCut).
- Feature Registry (backend y frontend): agregar una herramienta nueva es registrar un módulo, sin tocar switches ni imports dispersos.
- CLIs standalone conservados: `clearcut` (remove/scale/batch/ensure-models) y `designfabric` (generación por lotes vía Ollama+FLUX.2), independientes de la app de escritorio.
- Ventana siempre maximizada, con la topbar nativa del sistema operativo visible y sin la barra de menú por defecto de Electron.
- Consola de logs en vivo (progreso del backend y del proceso principal) integrada en la UI.
- Sistema de versionado con un único archivo `VERSION` como fuente de verdad, sincronizado a `package.json`/`pyproject.toml` vía `npm run version:sync` / `version:check`.
- Sistema de empaquetado (`npm run release`) que genera un `.AppImage` (Linux) y un `.exe` portable (Windows) livianos: el instalador no incluye las dependencias de IA (torch/diffusers/transformers, varios GB); estas se instalan en el primer arranque.
- Wizard de primer arranque: al abrir la app empaquetada por primera vez, permite elegir instalar el módulo de generación por IA local en ese momento o diferirlo para más adelante.
- Degradación elegante del backend cuando el módulo de IA local no está instalado: las herramientas de ClearCut (CPU) funcionan igual, y las de generación IA muestran un estado "no instalado" con opción de instalarlo después sin reiniciar la app. Endpoint `GET /features` reporta qué módulos están disponibles.
- Diálogos nativos de selección de archivo/carpeta y de exportación de imágenes, y apertura de carpetas de salida en el explorador del sistema.
- Suites de test heredadas y adaptadas de ambos proyectos originales (pytest para el backend, incluyendo cobertura nueva para el sistema de jobs, el feature registry y la degradación sin IA local).
