# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DesignFabric is a monorepo fusing two former projects — **ClearCut** (background removal +
upscaling) and **DesignFabric** (sticker generation via Ollama + FLUX.2 Klein) —
into one Electron desktop app backed by a single FastAPI backend. All tools live as tabs of one
tabpane: background removal, scale, ClearCut batch processing, AI batch generation, and
AI single-image generation.

## Commands

```bash
# Setup (backend uv sync + frontend npm install)
npm run setup

# Backend dev server (FastAPI, port 8756)
cd backend && uv run uvicorn designfabric.api.app:app --reload --port 8756
# or from repo root:
npm run backend

# Backend tests
cd backend && uv run pytest -v          # or: npm run test:core / npm run test
uv run pytest tests/api/test_jobs.py    # single file
uv run pytest tests/api/test_jobs.py::test_name -v   # single test
uv run pytest -m "not integration"      # skip tests needing AI models/CUDA

# Backend lint/typecheck
cd backend && uv run ruff check .
cd backend && uv run mypy src

# Frontend typecheck
npm run typecheck   # runs tsc --noEmit for both node and web tsconfigs

# Desktop app (spawns the backend automatically)
npm run dev

# Standalone CLIs (no Electron required)
uv run clearcut remove ...
uv run clearcut scale ...
uv run designfabric --n 5

# Versioning: VERSION file is the single source of truth
npm run version:check   # verify package.json/pyproject.toml match VERSION
npm run version:sync    # sync them

# Packaging (produces .AppImage / portable .exe; AI deps installed on first launch)
npm run build:app
npm run release
```

## Architecture

### Two processes, one contract

The Electron app never talks to Python domain code directly — it spawns a FastAPI backend
(`backend/src/designfabric/api/app.py`) as a child process and speaks HTTP + WebSocket to it
(`apps/desktop/src/main/backend-process.ts` spawns `uv run uvicorn ...`, polls `/health`, and
streams the child's stdout/stderr into the in-app log console). In dev, it uses the `uv` on PATH
against the repo's `backend/`. In packaged builds, `pythonSetup.ts` copies `backend/` into
`userData` and runs `uv sync` there on first launch (or after an update) so `backend/` stays a
self-contained Python package with no path dependencies outside itself — this is also why
`backend/README.md` exists standalone.

The backend serves a `local-ai` optional dependency group (torch/diffusers/transformers/ollama —
several GB) that is *not* bundled in the installer. `GET /features` reports whether it's
installed; the desktop app shows a first-run wizard (`SetupWizard.tsx`) to install it then or
defer, and the AI tabs render a "not installed" state via `FeatureNotInstalled.tsx` until it is.
`api/registry.py` degrades gracefully: it `try/except ImportError`s the GPU-only routers
(`batch_generation`, `single_image`) and sets `LOCAL_AI_AVAILABLE` accordingly — ClearCut's
CPU-only tools keep working regardless.

### Feature Registry pattern (both sides)

Adding a new tool/tab means registering one module — no `if/else` or import scattered across
switches:

- **Backend** (`backend/src/designfabric/api/registry.py`): `FEATURE_REGISTRY` is a tuple of
  `FeatureModule` entries, each bundling a name, an `APIRouter`, the `JobType`s it produces, its
  `worker_affinity` (`"gpu"` or `"cpu"`), and a `build_handlers(settings, store)` factory.
  `app.py`'s `create_app()` iterates the registry to mount routers and build each worker's handler
  dict — it has zero feature-specific logic itself.
- **Frontend** (`apps/desktop/src/renderer/src/core/registry/featureRegistry.ts`): a `Map`-backed
  singleton that each feature module registers a `TabDescriptor` into on import (see
  `features/index.ts`), so `App.tsx` never needs to know the feature list up front.

### Mockups deterministas de prendas

Las herramientas «Mockups» y «Plantillas de mockup» viven en `features/mockups/` y
`features/mockup-templates/`. El render de producción es exclusivamente CPU (numpy, OpenCV y
Pillow), sin IA, GPU ni aleatoriedad; tanto `POST /api/mockups/preview` como el job de
`POST /api/mockups` usan el mismo `render_mockup`. El preview reduce primero plantilla y diseño
con Lanczos y limita `max_side` a 1280; los resultados son PNG RGB a 300 DPI.

El formato de plantilla v1 es una carpeta dentro de `DESIGNFABRIC_MOCKUP_TEMPLATES_DIR` (por
defecto `backend/data/mockup_templates/`): `template.json`, `base.png` RGB, `garment_mask.png` L,
`shading.png` L, `displacement.png` L y `occlusion.png` L opcional. Todas las imágenes tienen el
tamaño congelado `base_size` del JSON. `print_area.corners` guarda cuatro puntos TL, TR, BR y BL
en píxeles de la foto base; también se congelan `px_per_cm`, límites imprimibles, anclaje, fuerzas,
colores y colores oscuros. `core/imaging/mockup/template.py` valida el contrato al cargarlo y
`core/imaging/mockup/prepare.py` crea propuestas editables fuera del render.

La API expone `GET /api/mockups/templates` y `GET /api/mockups/templates/{id}/thumbnail`, el
preview síncrono `POST /api/mockups/preview`, el job CPU `POST /api/mockups`, y los endpoints
internos de preparación/guardado `POST /api/mockups/templates/prepare` y
`PUT /api/mockups/templates/{id}`. Los payloads usan snake_case; el job termina en
`GET /api/jobs/{job_id}` con `output_path` e `image_url` bajo `/output/mockups/`. El contrato del
motor vive en `core/imaging/mockup/` y la integración HTTP en `api/routers/mockups.py`.

### Async job system: GPU vs CPU worker pools

All heavy work (background removal, upscaling, AI generation) runs as an async job, not inline in
a request handler. `backend/src/designfabric/jobs/`:

- `JobDispatcher` routes a submitted job to the GPU or CPU `JobQueue` based on the
  `affinity_by_type` map built from `FEATURE_REGISTRY` in `app.py`.
- `GpuJobWorker` runs a **single** daemon thread — Ollama and FLUX.2 share VRAM and cannot run
  concurrently, so GPU jobs are strictly serialized.
- `CpuJobWorker` runs a **pool** of `cpu_count() - 1` daemon threads — ClearCut's onnxruntime/CPU
  work parallelizes fine.
- Neither worker class knows about any specific feature: `JobHandler` callables are injected from
  the registry's `build_handlers`, so a new job type never requires touching `worker.py`.
- Progress updates flow back through `WebSocketProgressReporter` / `ProgressHub`
  (`jobs/ws_reporter.py`), bound to the FastAPI event loop captured at `lifespan` startup (workers
  run on plain threads, so this is how thread → asyncio-loop progress publishing works) and
  consumed by the frontend via `useJobProgress.ts`.

### Background removal Strategy pattern

Background removal is a general imaging concern (not sticker-only). The public contract is
`BackgroundRemovalStrategy.remove_background(bgr) -> bgra` in
`core/imaging/background_removal_strategies.py`. The orchestrator
(`BackgroundRemover` / `process_image`) only loads, delegates, and saves — each strategy owns
its full internal pipeline (including any silhouette detection, erosion, or neural matting).

Registered strategies (`StrategyName` + `create_background_removal_strategy`):

- `white_background` / `color_background` — classical OpenCV silhouette phases + erosion
- `sam2_vitmatte` — SAM2 Tiny ONNX + ViTMatte ONNX + Guided Filter (`core/imaging/sam2_vitmatte/`);
  matting pipeline tuned for photos (soft edges) — trimap + neural alpha blending
- `isnet_general` — IS-Net general-use ONNX, single-pass saliency segmentation, no trimap/matting
  (`core/imaging/isnet_strategy.py`); hard, consistent edges — the recommended default for flat
  illustrations/stickers
- `rembg_illustration` — IS-Net-anime via the `rembg` library (`core/imaging/rembg_strategy.py`),
  trained specifically on anime/2D illustration art
- `birefnet_sam2_matte` — BiRefNet (primary, via `rembg`) → SAM2 (optional refinement, only if
  configured) → ViTMatte or BRIA RMBG (auto-selected: ViTMatte if configured, else BRIA via
  `rembg`) → guided filter (`core/imaging/birefnet_sam2_matte_strategy.py`)

Local ONNX paths for SAM2/ViTMatte/IS-Net general are configured in the desktop Settings →
«Modelos locales» (SAM2 encoder + SAM2 decoder + ViTMatte + IS-Net general; persisted in
`userData`, synced via env `DESIGNFABRIC_SAM2_ENCODER_ONNX` / `DESIGNFABRIC_SAM2_DECODER_ONNX` /
`DESIGNFABRIC_VITMATTE_ONNX` / `DESIGNFABRIC_ISNET_GENERAL_ONNX` and `PUT /api/settings/model-paths`).
`rembg_illustration` and `birefnet_sam2_matte` instead manage their own models (BiRefNet, BRIA
RMBG, IS-Net-anime) via `rembg`, which downloads and caches them on first use (needs internet
that first time; no path configuration needed) — `birefnet_sam2_matte` opportunistically reuses
the SAM2/ViTMatte paths above when present. The UI strategy list comes from
`GET /api/clearcut/strategies`.

### Backend layout

`backend/src/designfabric/`:
- `api/` — FastAPI layer: `app.py` (factory), `registry.py` (feature registry), `routers/` (one
  module per feature, each exposing a `router` + `build_handlers`), `dispatcher.py`,
  `schemas.py`/`serializers.py`.
- `core/` — domain logic, framework-agnostic: `imaging/` (background removal strategies,
  upscaling strategies incl. AI upscalers, batch processing pipeline) and
  `generation/` (Ollama prompt generation + FLUX.2 Klein sticker pipeline).
- `jobs/` — the queue/worker/dispatcher system described above.
- `cli/` — standalone Typer/Rich-based CLIs (`clearcut`, `designfabric`) that call the same `core/`
  domain code directly, independent of the API/Electron.

### Frontend layout

`apps/desktop/src/`:
- `main/` — Electron main process: window management, backend process lifecycle
  (`backend-process.ts`, `pythonSetup.ts`, `runtime.ts`), IPC setup, log store, preferences.
- `preload/` — context-bridge IPC surface exposed to the renderer.
- `renderer/src/core/` — shared infra: feature registry, API HTTP client, shared hooks
  (`useJobProgress`, `useLocalAiAvailability`, ...), shared components (`TabPane`,
  `JobProgressPanel`, `SetupWizard`, `FeatureNotInstalled`, ...).
- `renderer/src/features/<feature>/` — one directory per tab (`remove-background`, `scale`,
  `clearcut-batch`, `designfabric-batch`, `designfabric-single`), each self-registering into the
  feature registry via its `index.ts`.

### Tests

Backend tests live in `backend/tests/`, mirroring `src/designfabric/` (`api/`, `core/imaging/`,
`core/generation/`, `jobs/`, `cli/`). Tests needing actual AI models or CUDA are marked
`integration` (`pytest -m "not integration"` to skip them). `backend/tests/api/conftest.py` sets up
the FastAPI test client/fixtures.
