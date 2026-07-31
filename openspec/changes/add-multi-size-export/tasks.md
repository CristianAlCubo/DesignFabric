## 1. Backend: sizing & zip primitives

- [x] 1.1 Add `resolve_percent_size(src_w, src_h, percent) -> (int, int)` alongside
      `resolve_target_size` in `core/imaging/ai_upscalers/common.py`
- [x] 1.2 Add `ZipOutputTarget` to `core/imaging/batch/output_targets.py` implementing the
      `OutputTarget` ABC: writes into an open `zipfile.ZipFile`, one subfolder per source image
      stem, reusing the existing `_2`/`_3` collision-disambiguation convention for duplicate stems
- [x] 1.3 Add a filename template renderer (tokens `{name}`, `{width}`, `{height}`, `{percent}`,
      `{prefix}`, default `{prefix}{name}`)
- [x] 1.4 Unit tests: percent sizing math, zip target collision handling, template rendering
      (including missing-token and default-template cases)

## 2. Backend: multi-export domain logic

- [x] 2.1 Define the size-row and preset request shapes (Pydantic schemas in `api/schemas.py`),
      e.g. `SizeRow {label, mode: "px"|"percent", width?, height?, percent?, prefix, template?}`
      and `MultiExportJobRequest {image_paths: list[str], sizes: list[SizeRow], output_name?}`
- [x] 2.2 Implement the N×M processing loop in `core/imaging/` (new module, e.g.
      `multi_export_pipeline.py`): for each image × size row, load, resize (`resize_bgra` +
      `resolve_target_size`/`resolve_percent_size`), render filename, write into the
      `ZipOutputTarget`; catch per-item failures without aborting the loop
- [x] 2.3 Produce a result payload mirroring `BatchReport.to_dict()`'s shape: `produced`,
      `expected`, `zip_path`, per-item `{image, size_label, status, error}` list
- [x] 2.4 Wire progress reporting through `core/progress.py` emit helpers, one update per
      completed image/size combination
- [x] 2.5 Unit tests: full pipeline happy path, partial-failure path (one item fails, rest
      succeed and are reported correctly)

## 3. Backend: job type, router, registry

- [x] 3.1 Add `JobType.MULTI_EXPORT` to `jobs/models.py`
- [x] 3.2 Create `api/routers/multi_export.py`: `router = APIRouter(...)`, `POST` endpoint that
      creates a `Job`, submits via dispatcher, returns `JobCreatedResponse` (202); `build_handlers`
      closure invoking the pipeline from section 2
- [x] 3.3 Register the new `FeatureModule` (CPU affinity) in `api/registry.py`'s `_cpu_modules`
- [x] 3.4 Add a route (or extend the job result) to serve/download the produced zip file
      (reused the existing `/output` static mount via a `zip_url` field, same as `image_url`)
- [x] 3.5 API-level tests (`backend/tests/api/`): job submission, polling to completion, result
      shape, zip download

## 4. Electron main: preset persistence & IPC

- [x] 4.1 Define shared preset types in `apps/desktop/src/shared/` (e.g.
      `multiExportPresets.ts`): `SizeRow`, `Preset { id, name, sizes, isBuiltin }`,
      `BUILTIN_MULTI_EXPORT_PRESETS` constant — ships empty by decision (see design.md Open
      Questions): app starts with zero factory presets, only user-created ones
- [x] 4.2 Create `apps/desktop/src/main/multi-export-presets.ts`: versioned JSON store in
      `userData` (atomic tmp+rename write, matching `model-path-preferences.ts`), merging built-in
      presets into `list()` results without persisting them
- [x] 4.3 Create `apps/desktop/src/main/multi-export-presets-ipc.ts`
      (`registerMultiExportPresetsIpc()`): handlers for `list/create/update/delete/duplicate`;
      reject `update`/`delete` on `isBuiltin` presets
- [x] 4.4 Add a preset-import handler (open dialog, `.json` filter, validates + auto-renames on
      name conflict) and a preset-export save handler (save dialog, `.json` filter, writes
      selected preset(s) with a `schemaVersion` field)
- [x] 4.5 Add `multiExport:downloadZip` handler (save dialog, `.zip` filter) for downloading the
      multi-export job's zip, mirroring `image:export`'s fetch+writeFile pattern
- [x] 4.6 Wire `registerMultiExportPresetsIpc()` into `main/index.ts` startup
- [x] 4.7 Add preload methods (`apps/desktop/src/preload/index.ts` + `index.d.ts`) for preset
      CRUD, import, export, and zip download

## 5. Frontend: multi-size export feature

- [x] 5.1 Scaffold new feature module `features/multi-export/`, self-registering into
      `featureRegistry` (sectionId `batches`, alongside "Lote")
- [x] 5.2 Build the store (Zustand) in `features/multi-export/store.ts`: multi-image picker
      state, presets (via IPC), active size rows, `useJobProgress`-driven job run/result state
- [x] 5.3 Build the preset selector + size-row editor UI (`MultiExportPanel.tsx` +
      `SizeRowEditor.tsx`): create/save-as/update/duplicate/delete, built-in presets shown without
      an edit/delete affordance (only duplicate)
- [x] 5.4 Build import/export UI for presets (invokes the IPC methods from 4.7)
- [x] 5.5 Build the run UI: image list, progress bar via `useJobProgress`, partial-failure
      summary + per-item result list, "Descargar .zip" action once the job completes
- [x] 5.6 Add the new tab entry point (`Multi-tamaño`) alongside the existing "Lote" tab

## 6. Verification

- [x] 6.1 Backend: `uv run pytest` (201 passed) and `uv run ruff check .` / `uv run mypy src`
      (no new errors; only pre-existing unrelated findings)
- [x] 6.2 Frontend: `npm run typecheck` (clean)
- [x] 6.3 Manual pass via the real desktop app (`npm run dev` on the user's machine): confirmed
      `/features` lists `multi-export`, ran a real 2-image × 2-size job end-to-end against the
      live backend (correct per-image zip subfolders, correct filenames), verified the new
      feature's renderer modules (`index.ts`, `store.ts`, `MultiExportPanel.tsx`,
      `SizeRowEditor.tsx`) compile and are wired into `features/index.ts`'s import graph with no
      Vite transform errors. Could not capture a visual screenshot (native Wayland session, no
      screenshot tool available) — UI interaction (image dialogs, preset CRUD) was verified by
      code review + typecheck, not visually confirmed.
