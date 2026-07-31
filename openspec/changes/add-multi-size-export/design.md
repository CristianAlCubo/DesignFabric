## Context

The Scale tab today (`api/routers/scale.py`, `features/scale/`) resizes one image to one target
size via a single-result CPU job, polled by the frontend (no WebSocket progress). ClearCut batch
(`core/imaging/batch/`, `features/clearcut-batch/`) already handles N source images through one
job, reporting per-item progress over WebSocket (`useJobProgress`) and writing one output file per
input to a flat `DirectoryOutputTarget`. Resize itself is plain OpenCV (`resize_bgra`,
`resolve_target_size` in `core/imaging/ai_upscalers/common.py`) — no PIL, no AI model involved
unless a size explicitly requests an AI upscale strategy (it won't, for this feature). There is no
zip-writing code anywhere in the repo, and no database — local persistence is hand-rolled
versioned JSON files in Electron's `userData` (`model-path-preferences.ts`,
`generation-preferences.ts`), each with a matching `register*Ipc()` module and preload methods.

This feature composes existing patterns (batch iteration, CPU job, OutputTarget abstraction,
userData JSON persistence) rather than introducing new infrastructure.

## Goals / Non-Goals

**Goals:**
- Resize N source images against M preset size rows (fixed px or percent), writing every
  resulting file into one `.zip`, organized as one subfolder per source image.
- Let a failed row/image be recorded as a partial failure without aborting the whole job, mirroring
  `BatchReport`/`BatchItemResult` and `upscale_pipeline.py`'s `_run_with_fallback` philosophy.
- Let users create, edit, duplicate, and delete named presets of size rows, ship a handful of
  built-in presets, and import/export presets as `.json` files.
- Reuse the existing Feature Registry, job system, and `OutputTarget` abstraction rather than
  building parallel infrastructure.

**Non-Goals:**
- No AI-upscaling path for sizes that exceed the source resolution — plain interpolation only,
  even when upscaling. (Mixing CPU-affinity batch resize with the serialized GPU upscale worker in
  one job is real added complexity; deferred.)
- No per-image preset override within a single run — one preset applies to all N images in a run.
- No cloud/remote storage of presets — local `userData` JSON only, matching every other settings
  store in the app.
- No cropping/padding/letterboxing modes in this iteration — fixed-size rows that don't match the
  source aspect ratio just resize disregarding original ratio unless only one dimension is given
  (in which case the existing aspect-preserving behavior in `resolve_target_size` applies).

## Decisions

**1. New `JobType.MULTI_EXPORT`, CPU worker affinity, new `FeatureModule`.**
Resize-only work is cheap CPU work identical in cost profile to `scale`/`clearcut_batch`. Adding a
`FeatureModule` entry (`worker_affinity="cpu"`) to `registry.py`'s `_cpu_modules` needs zero changes
to `app.py`, `JobDispatcher`, or `CpuJobWorker` — confirmed by reading `jobs/worker.py`: handlers
are injected, `Job.result` is untyped `Any`, so returning `{"zip_path": ..., "items": [...]}` needs
no schema change.
*Alternative considered*: extend `JobType.SCALE`'s existing handler with an optional "multi" mode.
Rejected — conflates two different result shapes (single file vs. zip-of-many) in one handler and
one frontend store; a dedicated job type keeps `scale.py` untouched and easier to reason about.

**2. New `ZipOutputTarget` implementing the existing `OutputTarget` ABC.**
`core/imaging/batch/output_targets.py` already defines `OutputTarget.resolve(input_path) -> Path`
with one concrete `DirectoryOutputTarget`. Add `ZipOutputTarget` that resolves paths *inside* an
open `zipfile.ZipFile` (subfolder-per-source-image, i.e. `resolve(input_path, size_label)` yields
an archive member path such as `{input_stem}/{prefix}{input_stem}.png`), reusing the same
collision-disambiguation convention (`_2`, `_3`, ...) `DirectoryOutputTarget` already implements
for same-named inputs.
*Alternative considered*: bespoke zip-writing code inline in the new router's handler. Rejected —
the `OutputTarget` abstraction already exists for exactly this seam, and a general
`ZipOutputTarget` is available for free to ClearCut batch later if wanted.

**3. Percentage sizing as a new pure helper, no changes to `upscale_strategies.py`.**
Add a small helper (e.g. `resolve_percent_size(src_w, src_h, percent) -> (w, h)`) alongside
`resolve_target_size` in `ai_upscalers/common.py`, then feed its output into the existing
`resize_bgra`. This entirely bypasses the `UpscaleStrategy`/model-loading machinery (RealESRGAN,
etc.) — multi-size export never touches GPU code paths.

**4. Frontend modeled on `features/clearcut-batch/`, not `features/scale/`.**
`clearcut-batch` already solves "N inputs, one job, live per-item progress via `useJobProgress`,
partial-failure display" — the same shape this feature needs (just N×M instead of N). `scale`'s
simple poll-until-done pattern doesn't fit a job that reports fine-grained per-item progress.
New UI adds: a preset selector/editor above the existing file-list-with-progress UI, and a
"Download zip" action once the job succeeds (reusing the `image:export` save-dialog IPC pattern,
generalized to arbitrary file bytes/URL rather than a single image).

**5. Presets persisted as versioned JSON in Electron `userData`, no database.**
Mirrors `model-path-preferences.ts` exactly: `multi-export-presets.json` with a `version` field,
atomic write (`.tmp` + `renameSync`), read-with-fallback-to-defaults. Built-in presets ship as a
constant (`DEFAULT_BUILTIN_PRESETS`) merged into the read result with `isBuiltin: true` and are
never persisted into the user's editable list (so app updates can add/adjust built-ins without a
migration). A new `registerMultiExportPresetsIpc()` module (mirroring
`model-path-settings-ipc.ts`) exposes `list/create/update/delete/duplicate`; `isBuiltin` presets
reject `update`/`delete` at the IPC layer (defense in depth beyond UI graying-out).
*Alternative considered*: SQLite via a new dependency. Rejected — no DB exists anywhere in the
repo today (verified via dependency search across both `package.json` and `pyproject.toml`); a
flat JSON file is consistent with every other piece of local state and is trivially
import/export-able as a file, which the feature needs anyway.

**6. Preset file export/import is a distinct operation from the internal store.**
"Export a preset" writes the preset object(s) (with a `schemaVersion` field, no `isBuiltin` flag)
to a user-chosen `.json` file via `dialog.showSaveDialog` (new channel, same pattern as
`image:export`). "Import" reads a user-chosen `.json` file via a new `dialog:openJsonFile` channel,
validates shape (reject unknown `schemaVersion`, malformed rows) before merging into the internal
store, and never silently overwrites an existing preset with the same name (append/rename-on-
conflict, surfaced to the user).

**7. Filename templating instead of a fixed prefix+name scheme.**
Each size row stores a `template` string using tokens `{name}` (source stem), `{width}`,
`{height}`, `{percent}`, `{prefix}` (defaults to `{prefix}{name}` if unset), rendered once per
row per image. This avoids re-litigating naming conventions later (e.g. `@2x` suffix presets) for
the cost of a single string-substitution function.

## Risks / Trade-offs

- **Large batches (N images × M sizes) could be slow or memory-heavy if the whole zip is built in
  memory.** → Stream writes: open the output zip on disk with `zipfile.ZipFile(path, "w")` and
  write each resized buffer as it's produced, rather than accumulating all variants in memory
  first (same "process then write" flow `batch/processor.py` already uses per item).
- **Partial failure reporting could hide the archive being genuinely incomplete.** → Zip filename
  and API response both surface a count (`"produced": 7, "expected": 8`) and the per-item error
  list, matching `BatchReport.to_dict()`'s existing shape, so the desktop UI can show a clear
  warning banner rather than a silent partial success.
- **Percent mode combined with a fixed-mode row in the same preset could confuse users about what
  "50%" means when images differ in size.** → Document (in the preset editor's row help text) that
  percent is always relative to each image's own original dimensions, not a shared reference size.
- **Built-in presets embedded as a frontend/main-process constant means updating them requires a
  new app release**, unlike user presets. → Acceptable for v1; flagged as an open question below in
  case a remote/config-driven built-in list is wanted later.

## Migration Plan

Purely additive: new job type, new router, new frontend feature surface, new IPC channels, new
`userData` file. No existing job types, routers, output targets, or preference files are modified.
Rollback is deleting the new module/registry entries; no data migration needed since
`multi-export-presets.json` is new and only ever read/written by the new code.

## Open Questions

- Should built-in presets eventually be config-driven (e.g. a bundled JSON shipped in `resources/`
  rather than a hardcoded constant) so they can be tuned without a full app release? Deferred —
  not needed for v1 scope.
- ~~Exact default set of built-in presets~~ Resolved: `BUILTIN_MULTI_EXPORT_PRESETS` ships empty —
  the app starts with zero factory presets, only user-created ones. The mechanism (`isBuiltin`,
  read-only enforcement, duplicate-to-edit) stays in place so presets can be added later without
  further plumbing changes.
