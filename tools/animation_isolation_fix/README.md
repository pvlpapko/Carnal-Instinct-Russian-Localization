# Animation isolation fix tools

Reproducibility tools used for the 2026-10-03 v5 release candidate.

- `locres_patch.py`: restores technical combat/AI/locomotion FText entries to exact English source values while preserving Namespace, Key and SourceStringHash.
- `pak_v3.py`: reads and rebuilds the one-file uncompressed UE Pak v3 localization container.
- `blake3_pure.py`: dependency-free BLAKE3 implementation validated against the standard empty-string and "abc" vectors.
- `iostore_simple.py`: parses/validates the uncompressed IoStore format used by the localization override and verifies chunk BLAKE3 hashes.
- `iostore_rebuild.py`: rebuilds a selected package subset, rewrites the directory index and container package store, and validates hashes/package IDs.

Release candidate: `Carnal_Instinct_RU_DontLook_AnimationIsolation_2026-10-03_v5.zip`

Release SHA-256: `09b794bf5f69cf996c6f5ceff856afe81b95a667f5415d4def45b05146edb4b1`

Important: these tools and reports establish static integrity; they do not replace an in-game runtime test.
