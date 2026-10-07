# Carnal Instinct Russian Localization

Russian localization, asset-analysis, UI-fix and installer workspace for **Carnal Instinct**.

**Author:** Don't Look

Original game assets and large cooked/binary containers stay outside GitHub. This repository stores source-controlled project state, translations, audit reports, tooling, installer source, source identities and resumable checkpoints.

## Editions

### NoSteam

NoSteam has a fixed baseline:

`0.7.9.16232`

Active NoSteam paths:

- `nosteam/0.7.9.16232/`
- `working/nosteam/0.7.9.16232/<task>/`

Unpacked read-only NoSteam source:

- Drive folder: `Carnal_Instinct_UE5_Nosteam`
- Drive ID: `1utEQ4N93dZ3PUJRO5M0jX5gg1BydoAQ1`
- Source state: `nosteam/0.7.9.16232/SOURCE_STATE.json`

NoSteam navigation manifests on Drive:

- `CI GPT/Manifests/CI_NOSTEAM_SOURCE_INDEX.json`
- `CI GPT/Manifests/CI_NOSTEAM_SOURCE_TREE.txt`

The NoSteam index contains an exact recursive folder catalog plus an exact logical cooked-asset/package catalog recovered from the matching `AssetRegistry.bin`. Extracted duplicate filenames and sidecars such as `.ubulk` are resolved from the exact indexed NoSteam parent folder before build-dependent use; they are never guessed from Steam metadata.

### Steam

Steam is a **rolling channel** and is deliberately **not bound to a version number in working paths**.

Active Steam work always uses:

- `steam/current/`
- `working/steam/current/<task>/`

Unpacked read-only Steam source:

- Drive folder: `Carnal_Instinct_UE5`
- Drive ID: `1-kOUHTe33iZDj4wvLk-KpA6rqWGvmFnC`

Steam navigation manifests on Drive:

- `CI GPT/Manifests/CI_SOURCE_INDEX.json`
- `CI GPT/Manifests/CI_SOURCE_TREE.txt`

The actual Steam version/build is metadata stored in `steam/current/BUILD_STATE.json` after it is verified from the current source. A Steam update does not require renaming the workspace or creating a new version directory.

When the Steam source changes, build-dependent binary/UI compatibility must be revalidated. Previous results remain available through Git history and explicit release/build snapshots when needed.

## Repository policy

Use this single repository for both editions. Do **not** create a second NoSteam repository: edition separation is represented by source state, paths and compatibility metadata.

GitHub stores state, manifests/summaries, translations, reports, scripts and installer source. Google Drive stores original unpacked sources, large binary assets, containers and releases.

## Persistent workflow

Every substantial audit, translation pass, build comparison, asset-analysis pass, UI change, source-index task or installer task must establish a persistent checkpoint **before expensive work begins**.

- NoSteam: `working/nosteam/0.7.9.16232/<task>/AUDIT_STATE.json`
- Steam: `working/steam/current/<task>/AUDIT_STATE.json`

See [PROJECT_RULES.md](PROJECT_RULES.md), [WORKFLOW.md](WORKFLOW.md) and [PROJECT_INSTRUCTION.md](PROJECT_INSTRUCTION.md).
