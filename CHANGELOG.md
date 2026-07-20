# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
