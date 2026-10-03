# Carnal Instinct Russian Localization

Russian localization, asset-analysis, UI-fix and installer workspace for **Carnal Instinct**.

**Author:** Don't Look

This repository stores source-controlled project state, translation tables, audit reports, validation tooling and installer source. Original game assets and large cooked/binary containers are not stored here.

## Editions

- **NoSteam** — baseline `0.7.9.16232`.
- **Steam** — tracked independently. The active Steam build must be verified from matching build evidence before binary/UI overrides are reused.

## Persistent workflow

Long-running work is resumable. Every substantial audit or modification must create/update a matching `working/<edition>/<build>/<task>/AUDIT_STATE.json` and checkpoint progress before moving to another expensive phase.

See [PROJECT_RULES.md](PROJECT_RULES.md) and [WORKFLOW.md](WORKFLOW.md).
