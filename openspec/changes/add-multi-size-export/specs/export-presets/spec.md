## ADDED Requirements

### Requirement: Local preset persistence
The system SHALL persist user-created export presets locally on the desktop (no external database
or network service), surviving app restarts, and SHALL NOT lose existing presets when the storage
schema version changes (falling back to defaults only when the store is missing or unreadable).

#### Scenario: Presets survive app restart
- **WHEN** a user creates a preset and restarts the application
- **THEN** the preset is still available in the preset list

### Requirement: Preset CRUD
The system SHALL let users create, edit, duplicate, and delete their own export presets. Each
preset SHALL consist of a name and an ordered list of size rows (as defined by the
`multi-size-export` capability).

#### Scenario: Create and reuse a preset
- **WHEN** a user creates a preset named "Thumbnails" with 3 size rows
- **THEN** "Thumbnails" appears in the preset list and can be selected for a subsequent
  multi-size export run without re-entering the size rows

#### Scenario: Delete a user preset
- **WHEN** a user deletes a preset they created
- **THEN** the preset no longer appears in the preset list and is not selectable for future runs

### Requirement: Built-in presets are read-only
The system SHALL ship with a set of built-in presets covering common use cases (e.g. thumbnails,
app icons, social media sizes), marked as built-in, and SHALL prevent users from editing or
deleting a built-in preset directly. Users SHALL be able to duplicate a built-in preset into an
editable user preset.

#### Scenario: Built-in preset cannot be deleted
- **WHEN** a user attempts to delete a built-in preset
- **THEN** the system rejects the deletion and the built-in preset remains available

#### Scenario: Duplicate a built-in preset for editing
- **WHEN** a user duplicates a built-in preset
- **THEN** a new user-owned, editable copy is created, and the original built-in preset is
  unchanged

### Requirement: Preset export to file
The system SHALL let a user export one or more presets to a `.json` file of the user's choosing,
containing enough information to fully reconstruct the preset(s) on import.

#### Scenario: Export a preset to a file
- **WHEN** a user exports the "Thumbnails" preset
- **THEN** the system writes a `.json` file, chosen by the user via a save dialog, containing the
  preset's name and size rows

### Requirement: Preset import with validation
The system SHALL let a user import presets from a `.json` file previously exported by this
feature, validating the file's structure before adding any preset, and SHALL reject files that do
not match the expected schema without corrupting the existing preset store. On a naming conflict
with an existing preset, the system SHALL NOT silently overwrite the existing preset.

#### Scenario: Successful import
- **WHEN** a user imports a previously exported, valid presets file
- **THEN** the presets it contains are added to the preset list and are selectable for a
  multi-size export run

#### Scenario: Invalid file rejected
- **WHEN** a user attempts to import a `.json` file that does not match the expected preset schema
- **THEN** the system rejects the import, leaves the existing preset store unchanged, and reports
  the error to the user

#### Scenario: Name conflict on import
- **WHEN** a user imports a preset whose name matches an existing preset
- **THEN** the system does not overwrite the existing preset, and instead either renames the
  imported preset or asks the user how to resolve the conflict
