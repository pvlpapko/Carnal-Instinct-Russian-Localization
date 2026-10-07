# Resumable Workflow

## Mandatory start procedure

Before substantial work:

1. Determine edition: NoSteam, Steam, or both.
2. Read `working/STATE_INDEX.json`.
3. Load the matching source state and index.
4. For Steam, verify the current rolling source.
5. Locate the matching working task.
6. Read its `AUDIT_STATE.json`.
7. Resume from `next_unit`.
8. If state is absent, create it before expensive analysis.

Source selection:

- NoSteam: `nosteam/0.7.9.16232/SOURCE_STATE.json`, `CI_NOSTEAM_SOURCE_INDEX.json`, `CI_NOSTEAM_SOURCE_TREE.txt`.
- Steam: `steam/current/BUILD_STATE.json`, `CI_SOURCE_INDEX.json`, `CI_SOURCE_TREE.txt`.
- Both: load both sets separately.

## Working paths

NoSteam:

`working/nosteam/0.7.9.16232/<task>/`

Steam:

`working/steam/current/<task>/`

## NoSteam physical-file resolution

The NoSteam source index contains an exact folder catalog and an exact logical AssetRegistry package/asset catalog.

Some extracted duplicate assets have generated filename suffixes, and sidecars such as `.ubulk` are separate physical files. When a NoSteam record has no verified physical file ID:

1. read the parent folder ID from `working/nosteam/0.7.9.16232/source_index/FOLDERS.json`;
2. list that exact folder on Drive;
3. select the exact file and required sidecars;
4. verify the metadata or bytes needed for the current task;
5. record that physical identity in the task report/state.

Edition-specific source identities remain separate.

## AUDIT_STATE.json minimum fields

- schema_version
- edition
- task
- status
- source_state_id
- verified_game_version
- verified_build
- created_at
- updated_at
- current_phase
- last_completed_unit
- next_unit
- completed_units
- pending_units
- source_files_used
- working_files
- validation_completed
- validation_pending
- notes

For Steam, verified version/build may be null when not proven.

## Stable work identifiers

Localization:

`Namespace + Key + original SourceStringHash`

Cooked asset:

`package/path + edition + source_state_id`

Resolved physical file:

`relative path + edition + source_state_id + verified file identity`

## Checkpoint policy

Commit checkpoints after completed translation batches, packages/subsystems, significant analysis results and meaningful artifacts, and before binary/container work or final validation.

Each checkpoint updates working data and `AUDIT_STATE.json` with explicit `last_completed_unit` and `next_unit`.

## Resume policy

On continuation:

1. determine edition;
2. read the matching source state/index;
3. read `working/STATE_INDEX.json`;
4. read the task state;
5. verify source identity;
6. skip completed verified units;
7. resume from `next_unit`.

If interruption occurred mid-unit, repeat only that unit.

## Steam source change policy

When Steam changes, keep the existing rolling workspace. Preserve compatible translation identities, revalidate build-dependent cooked/UI work, update source metadata and continue from the earliest affected unit.

## NoSteam source replacement policy

NoSteam stays fixed at 0.7.9.16232. If its unpacked source is re-exported, compare source identity and AssetRegistry hash, refresh the NoSteam index only when needed, and invalidate only work affected by changed bytes/schema.

## Finalization

Complete a task only after required phases and validation are recorded, reports are committed, external release artifacts are in their intended location, and runtime-test status is stated accurately.
