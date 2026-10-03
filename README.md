# Carnal Instinct Russian Localization

Russian localization, asset-analysis, UI-fix and installer workspace for **Carnal Instinct**.

**Author:** Don't Look

Original game assets and large cooked/binary containers stay outside GitHub. This repository stores source-controlled project state, translations, audit reports, tooling, installer source and resumable checkpoints.

## Editions

### NoSteam

NoSteam has a fixed baseline:

`0.7.9.16232`

NoSteam state may therefore use the build in its path.

### Steam

Steam is a **rolling channel** and is deliberately **not bound to a version number in working paths**.

Active Steam work always uses:

`steam/current/`

`working/steam/current/<task>/`

The actual Steam version/build is metadata stored in `steam/current/BUILD_STATE.json` after it is verified from the current source. A Steam update does not require renaming the workspace or creating a new version directory before work can continue.

When the Steam source changes, build-dependent binary/UI compatibility must be revalidated. Previous results remain available through Git history and explicit release/build snapshots when needed.

## Persistent workflow

Every substantial audit, translation pass, build comparison, asset-analysis pass, UI change or installer task must establish a persistent checkpoint **before expensive work begins**.

- NoSteam: `working/nosteam/0.7.9.16232/<task>/AUDIT_STATE.json`
- Steam: `working/steam/current/<task>/AUDIT_STATE.json`

See [PROJECT_RULES.md](PROJECT_RULES.md) and [WORKFLOW.md](WORKFLOW.md).
