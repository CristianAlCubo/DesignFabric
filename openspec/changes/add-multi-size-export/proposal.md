## Why

Users need to derive several sized/renamed copies of an image (thumbnails, marketplace assets,
app icons, alternate crops) in one pass instead of running the existing single-image `scale` tool
repeatedly and renaming files by hand. Doing this for a batch of source images multiplies the
manual work further. A dedicated multi-size export mode, paired with reusable named presets,
turns a repetitive manual export chore into a one-click batch operation.

## What Changes

- Add a "Multi-size export" mode to the existing Scale tab: pick N source images, pick one preset
  (a named list of size rows), run one job that produces every `image × size` combination and
  packages the results into a single downloadable `.zip` (one subfolder per source image, named
  files per size row using a filename template).
- Support two sizing modes per row: fixed pixel dimensions (aspect-preserving if only one
  dimension is given) and percentage-of-original. No AI upscaling — plain resize only, even when
  a requested size exceeds the original (classical interpolation, same as today's non-AI resize
  path).
- Add a new backend job type (`MULTI_EXPORT`, CPU worker affinity) and API route that runs the
  resize/zip pipeline and reports per-item progress, tolerating partial failures (a failed size
  or image is recorded but does not abort the rest of the job).
- Add a `ZipOutputTarget` implementing the existing `OutputTarget` abstraction in
  `core/imaging/batch/output_targets.py`, so the zip-writing capability is a general primitive,
  not one-off code.
- Add export presets: user-defined, named lists of size rows (label, mode, dimensions/percent,
  filename prefix/template), persisted locally in the desktop app (no database), with:
  - A small set of read-only built-in presets (e.g. common thumbnail/icon/social sizes).
  - Create/edit/duplicate/delete for user presets.
  - Export a preset (or set of presets) to a `.json` file and import one back, with validation.

## Capabilities

### New Capabilities
- `multi-size-export`: batch image resize into N×M variants packaged as a downloadable zip,
  including sizing modes, filename templating, progress reporting, and partial-failure handling.
- `export-presets`: CRUD and local persistence of named size-list presets (including built-in
  presets), plus file-based export/import of presets.

### Modified Capabilities
- None — this is a greenfield OpenSpec repo (`openspec/specs/` is currently empty); no existing
  spec-tracked capability changes behavior as part of this change.

## Impact

- **Backend**: new `JobType.MULTI_EXPORT`; new router module (e.g.
  `api/routers/multi_export.py`) + `FeatureModule` entry in `api/registry.py` (CPU affinity); new
  domain logic in `core/imaging/` for percentage-based sizing and the N×M resize loop; new
  `ZipOutputTarget` in `core/imaging/batch/output_targets.py`.
- **Frontend**: new mode/panel under `apps/desktop/src/renderer/src/features/scale/` (or a
  sibling feature module), modeled on `features/clearcut-batch/` for multi-item progress UI; new
  preset management UI (list, create/edit, duplicate, delete, import, export).
- **Electron main process**: new `multi-export-presets.ts` (userData JSON store, atomic writes,
  versioned schema) mirroring `model-path-preferences.ts`; new IPC handlers for preset CRUD and
  for preset/zip file import-export dialogs; preload + `index.d.ts` updates to expose them.
- **No changes** to GPU worker, AI upscale strategies, or existing background-removal/scale
  single-image behavior.
