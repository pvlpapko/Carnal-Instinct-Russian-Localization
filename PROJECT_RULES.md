# Project Rules

## Scope

Project: Carnal Instinct Russian Localization  
Author: Don't Look

Goals: Russian localization, asset analysis, UI fixes, installer work and validation for NoSteam and Steam while preserving gameplay, input, saves, progression and performance.

## Edition separation

NoSteam and Steam are separate compatibility domains.

### NoSteam

Fixed baseline:

- Game version: 0.7.9
- Build: 0.7.9.16232
- UE: 5.5.4
- ProductVersion: ++UE5+Release-5.5-CL-40574608

Use build-qualified NoSteam paths.

### Steam

Steam is rolling and must not use a version number as the primary working path.

Use:

- `steam/current/`
- `working/steam/current/<task>/`

The actual verified Steam version/build belongs in metadata, not in the active workspace path.

At the start of each Steam task or continuation, verify whether the source changed before reusing build-dependent binary/UI overrides.

Strong build/source evidence, in descending preference:

1. executable ProductVersion / file version;
2. Build.version / app manifest / package manifests;
3. container identities, sizes and hashes;
4. localization, cooked-asset or schema changes;
5. filenames and dates only as secondary evidence.

If the source changed:

- update `steam/current/BUILD_STATE.json`;
- mark build-dependent binary/UI compatibility as requiring revalidation;
- do not silently reuse previous cooked binary overrides;
- keep translation work only where key/hash/source compatibility remains verified;
- preserve prior state through Git history or explicit snapshots.

If the exact Steam build cannot be proven, set it to unknown/unverified rather than inventing it.

## Sources

Original game source is read-only unless explicitly allowed.

Primary source navigation remains:

- `CI_SOURCE_INDEX.json`
- `CI_SOURCE_TREE.txt`

Large original game assets, PAK/UTOC/UCAS containers and large cooked binaries stay on Google Drive or the original source store. Do not mirror them into GitHub.

GitHub stores:

- project state;
- translation tables;
- audit queues;
- reports;
- scripts;
- installer source;
- manifests;
- hashes and identities;
- reproducible validation metadata.

## Localization integrity

Preserve exact:

- Namespace;
- Key;
- original SourceStringHash;
- English source/hash relation;
- placeholders;
- tags;
- escapes;
- newlines.

Never hash Russian text.  
Never deduplicate solely by identical English text.  
Never translate technical identifiers merely because they are visible strings.

Preserve internal names such as:

- montage names;
- row/internal IDs;
- object/package paths;
- bindings;
- event/function names;
- save-slot identifiers.

Translate at display boundaries.

## Binary and cooked assets

Before modification, inspect architecture, dependencies, serialization, class/CDO schemas and handlers.

Do not perform blind byte patches.

For build-dependent cooked assets, verify matching source identity before reuse.

A prior Steam override is not assumed compatible with the next Steam update.

## Persistent work

Long tasks must be resumable.

The authoritative WIP state is the committed GitHub checkpoint, not chat context and not temporary local/container files.

Every substantial task must use a matching `AUDIT_STATE.json` as defined in WORKFLOW.md.

## Validation

Separate:

- historical reports;
- current static validation;
- actual in-game/runtime tests.

Never claim runtime compatibility unless actually tested.

Do not ship original global game containers.

Final release artifacts remain separated by edition and verified compatibility state.
