# Resumable Workflow

## Mandatory start procedure

Before substantial work:

1. Read the source index.
2. Determine edition: NoSteam or Steam.
3. For Steam, refresh or verify `steam/current/BUILD_STATE.json`.
4. Locate the matching working task.
5. Read existing `AUDIT_STATE.json` if present.
6. Resume from `next_unit`.
7. If no task state exists, create it before expensive analysis begins.

## Working paths

NoSteam:

`working/nosteam/0.7.9.16232/<task>/`

Steam rolling channel:

`working/steam/current/<task>/`

Steam task paths do not change when the game updates.

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

For Steam, `verified_game_version` and `verified_build` may be null when not yet proven. Never invent them.

## Stable work identifiers

Localization rows:

`Namespace + Key + original SourceStringHash`

Cooked assets:

`package/path + edition + source_state_id`

Subsystem work:

exact package/subsystem path.

## Checkpoint policy

Commit a checkpoint:

- after every completed translation batch;
- after every completed package/subsystem;
- after a significant asset-analysis result;
- after generating or modifying a meaningful artifact;
- before another expensive phase;
- before binary/container work;
- before final validation;
- whenever repeating completed work would be wasteful.

A checkpoint should update both working data and `AUDIT_STATE.json`.

The state must record explicit `last_completed_unit` and `next_unit`.

## Resume policy

On Retry, continuation or new chat:

1. read the current source index;
2. read the task state;
3. verify source identity;
4. skip completed verified units;
5. resume exactly from `next_unit`.

If interruption occurred mid-unit, repeat only that incomplete unit.

## Steam source change policy

Steam is a rolling source.

If current source identity differs from the state recorded by a task:

- do not discard the task;
- mark source compatibility as changed;
- invalidate only work that depends on the changed source/schema;
- preserve compatible translation rows whose source/key/hash identity still matches;
- revalidate cooked binary/UI overrides;
- update `source_state_id`;
- continue from the earliest actually affected unit.

Do not create a new version-bound workspace merely because Steam updated.

Git history is the default history mechanism. Explicit snapshots are created only when a release, regression comparison or compatibility investigation requires one.

## Finalization

A task becomes complete only when:

- required phases are complete;
- validation is recorded;
- final reports are committed;
- release artifacts are produced in the correct external/output location;
- runtime-test status is stated accurately.

Working state must never silently replace a verified release.
