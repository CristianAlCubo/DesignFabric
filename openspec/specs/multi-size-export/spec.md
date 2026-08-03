# multi-size-export

## Purpose

Export one or more source images against a size list (preset or ad-hoc), producing one resized output per image/size combination, packaged into a single downloadable `.zip`. CPU-only classical resizing, with per-item progress and partial-failure resilience. Surfaced as the "Multi-tamaño" tab in the "Lotes" section.

## Requirements

### Requirement: Batch multi-size export job
The system SHALL accept a job consisting of one or more source images and one size list (a
preset or an ad-hoc list of size rows), and SHALL produce, for every combination of source image
and size row, one resized output file, packaged together into a single downloadable `.zip`
archive.

#### Scenario: Single image, multiple sizes
- **WHEN** a user submits 1 source image and a size list with 3 rows
- **THEN** the resulting archive contains 3 output files, one per size row, for that image

#### Scenario: Multiple images, multiple sizes
- **WHEN** a user submits N source images and a size list with M rows
- **THEN** the resulting archive contains N × M output files in total, M per source image

### Requirement: Fixed-dimension and percentage sizing modes
Each size row SHALL specify either fixed pixel dimensions or a percentage of the source image's
own dimensions. For fixed dimensions, if only one of width/height is given, the system SHALL
compute the missing dimension preserving the source image's aspect ratio. For percentage mode,
the system SHALL compute the target width and height relative to that specific source image's own
original dimensions, not any other image in the batch.

#### Scenario: Fixed width only, aspect preserved
- **WHEN** a size row specifies `width: 200` with no height, against a source image of 400×300
- **THEN** the output is generated at 200×150

#### Scenario: Percentage relative to each source image
- **WHEN** a size row specifies `percent: 50` and the batch contains a 4000×3000 image and a
  300×200 image
- **THEN** the first image's output is 2000×1500 and the second image's output is 150×100

### Requirement: Filename templating per size row
Each size row SHALL support a filename template containing tokens `{name}` (source file stem),
`{width}`, `{height}`, `{percent}`, and `{prefix}`. If a row does not specify a template, the
system SHALL default to `{prefix}{name}`.

#### Scenario: Default template
- **WHEN** a size row has `prefix: "thumb_"` and no explicit template, applied to source `gato.png`
- **THEN** the output filename is `thumb_gato.png`

#### Scenario: Custom template with size tokens
- **WHEN** a size row has `template: "{name}@{width}x{height}"`, `width: 200`, `height: 150`,
  applied to source `gato.png`
- **THEN** the output filename is `gato@200x150.png`

### Requirement: Zip archive structure and name collision handling
The system SHALL organize output files inside the archive into one subfolder per source image
(named after that image's stem), and SHALL disambiguate two source images that produce the same
subfolder name by appending a numeric suffix, consistent with the existing directory output
target's collision convention.

#### Scenario: Per-image subfolders
- **WHEN** source images `gato.png` and `perro.png` are each exported to 2 sizes
- **THEN** the archive contains a `gato/` folder with 2 files and a `perro/` folder with 2 files

#### Scenario: Duplicate source stem across different input paths
- **WHEN** two source images from different folders both have the stem `photo`
- **THEN** the archive contains `photo/` and `photo_2/` subfolders, each with that image's outputs

### Requirement: Per-item progress reporting
While a multi-size export job runs, the system SHALL report progress incrementally as each
image/size combination completes, rather than only reporting completion at the end of the job.

#### Scenario: Progress updates during a multi-item job
- **WHEN** a job processing 2 images × 3 sizes is running
- **THEN** the client receives progress updates as each of the 6 outputs completes, not only a
  single update at job end

### Requirement: Partial failure resilience
If generating one image/size combination fails, the system SHALL record that failure and continue
processing the remaining combinations rather than aborting the entire job. The final job result
SHALL report the count of successfully produced files, the count expected, and details of any
failures.

#### Scenario: One size fails, others succeed
- **WHEN** 1 of 6 expected image/size combinations fails during processing (e.g. corrupt source
  decode)
- **THEN** the job completes with 5 files in the archive, and the result reports 5 produced out of
  6 expected along with the failure detail for the failed combination

### Requirement: CPU-only resize processing
Multi-size export SHALL use classical (non-AI) image resizing for every size row, including rows
that request dimensions larger than the source image, and SHALL NOT invoke any GPU-based AI
upscaling strategy.

#### Scenario: Requested size exceeds source resolution
- **WHEN** a size row requests dimensions larger than the source image's original resolution
- **THEN** the system produces an enlarged output using classical interpolation without invoking
  an AI upscaling model
