# Project Rules

## Scope

Project: Carnal Instinct Russian Localization  
Author: Don't Look

Goals: Russian localization, asset analysis, UI fixes, installer work and validation for NoSteam and Steam while preserving gameplay, input, saves, progression and performance.

## Edition separation

NoSteam and Steam are separate compatibility domains. Source files, cooked overrides, hashes, Drive IDs and compatibility results must remain edition-qualified.

### NoSteam

Fixed baseline:

- Game version: 0.7.9
- Build: 0.7.9.16232
- UE: 5.5.4
- ProductVersion: ++UE5+Release-5.5-CL-40574608

Paths:

- `nosteam/0.7.9.16232/`
- `working/nosteam/0.7.9.16232/<task>/`
- `nosteam/0.7.9.16232/SOURCE_STATE.json`

Unpacked NoSteam source:

- `Carnal_Instinct_UE5_Nosteam`
- Drive ID `1utEQ4N93dZ3PUJRO5M0jX5gg1BydoAQ1`

Navigation:

- `CI GPT/Manifests/CI_NOSTEAM_SOURCE_INDEX.json`
- `CI GPT/Manifests/CI_NOSTEAM_SOURCE_TREE.txt`
- folder catalog: `working/nosteam/0.7.9.16232/source_index/FOLDERS.json`

The NoSteam folder catalog is exact. The logical cooked package/asset catalog comes from the matching `AssetRegistry.bin`. Extracted duplicate files can have generated or non-sequential suffixes, and sidecars such as `.ubulk` are not logical AssetRegistry packages. Before build-dependent use, resolve the exact physical filename and Drive ID by listing the indexed NoSteam parent folder and verify its current metadata/bytes. Never fabricate a physical filename.

### Steam

Steam is rolling.

Paths:

- `steam/current/`
- `working/steam/current/<task>/`
- `steam/current/BUILD_STATE.json`

Unpacked Steam source:

- `Carnal_Instinct_UE5`
- Drive ID `1-kOUHTe33iZDj4wvLk-KpA6rqWGvmFnC`

Navigation:

- `CI GPT/Manifests/CI_SOURCE_INDEX.json`
- `CI GPT/Manifests/CI_SOURCE_TREE.txt`

Actual Steam version/build belongs in metadata, not the active path. Before reusing build-dependent binary/UI overrides, verify the current Steam source.

Evidence priority:

1. executable ProductVersion / file version;
2. Build.version / app manifest / package manifests;
3. container identities, sizes and hashes;
4. localization, cooked-asset or schema changes;
5. filenames and dates as secondary evidence.

If Steam changed, update `steam/current/BUILD_STATE.json`, preserve compatible translation identities, revalidate cooked overrides, invalidate only affected work and continue from the earliest affected unit. If the exact build cannot be proven, store null/unknown.

## Source selection

Determine edition before choosing an index.

- Steam -> Steam index/tree + Steam BUILD_STATE.
- NoSteam -> NoSteam index/tree + NoSteam SOURCE_STATE.
- Both -> both source states and both indexes.

Never overwrite or merge edition indexes. `Content.zip` is not used.

Large binary assets and releases stay on Drive. GitHub stores state, translations, reports, scripts, installer source, compact manifests, hashes and checkpoints.

## Localization integrity

Preserve exact Namespace, Key, original SourceStringHash, source/hash relation, placeholders, tags, escapes and newlines.

Never hash Russian text or deduplicate solely by identical English. Preserve internal IDs, paths, montage names, bindings, events/functions and save-slot identifiers. Translate at display boundaries.

## Binary and cooked assets

Before modification, inspect architecture, dependencies, serialization, class/CDO schemas and handlers. Do not perform blind byte patches.

For build-dependent work, verify matching edition, source_state_id and exact physical bytes. Matching logical package paths alone do not prove cross-edition compatibility.

## Persistent work

The authoritative WIP state is the committed GitHub checkpoint. Every substantial task uses a matching `AUDIT_STATE.json` as defined in WORKFLOW.md.

## Validation

Separate historical reports, static validation and in-game/runtime tests. Never claim runtime compatibility unless actually tested. Final release artifacts stay separated by edition and verified compatibility state.
