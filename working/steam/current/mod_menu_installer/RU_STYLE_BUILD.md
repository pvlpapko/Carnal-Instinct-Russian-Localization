# CI Mod Menu v1.1.1 — localization-style installer

This installer intentionally reuses the **exact Win32 wizard UI/layout** from the localization release template:

`Carnal_Instinct_RU_DontLook_2026-10-06_v18.13_RELEASE.zip/Developer/Installer_Source/`

No layout, color, wizard-page, DPI, footer, button, review/progress or folder-picker geometry changes were made. Only product-specific text, payload/state names, branding and mod cleanup logic were adapted.

## UI flow

1. License agreement.
2. Game version.
3. Game folder.
4. Review.
5. Progress/result.

The same cache-cleanup action and folder normalization from the localization installer are preserved.

## Edition mapping

- `Steam` -> `Steam_current`
- `NoSteam 0.7.9.16232` -> `NoSteam_0.7.9.16232`
- `NoSteam 0.7.9.16313 / 16315+` -> `Steam_current`

The third option deliberately aliases the rolling Steam payload. Future compatible NoSteam builds therefore consume the updated `Steam_current` files without creating a separate newer-NoSteam payload directory.

Current Steam source: 0.7.9.16321.

## Owned files

Current:
- CI_ModMenu_P.pak
- CI_ModMenu_P.utoc
- CI_ModMenu_P.ucas

Legacy names removed after successful replacement:
- CI_Mod_Menu_P.pak
- CI_Mod_Menu_P.utoc
- CI_Mod_Menu_P.ucas

Install state:
- `CI_ModMenu_Installed.json`

No persistent backups are created. Replacement rollback uses memory only if an install fails before commit.

## Trusted previous mod versions

Known hashes from v1.0.5, v1.1.0 and v1.1.1 are accepted so an existing older mod can be upgraded in place.

## Build

Go 1.23, Windows x64, CGO disabled. The original localization installer resource patcher is reused, with only manifest identity/description changed to CI Mod Menu.

Output:
- `CI_Mod_Menu_v1.1.1_Setup.exe`
- SHA-256: `15c226f80c10d4221d3a5a2f5dc0f195a4d78b4b466fa89a90a9c9f675f7a0ec`
- bytes: 3058176
- PE32+ x86-64 GUI
- 9 PE sections
- icon group: 9 sizes
- requireAdministrator manifest

Release package SHA-256:
`335b86ac008d1cbe78aeb04d2341c0f9b12fd06524dd3068e570812475320fe3`

Source archive SHA-256:
`f1fb8100526d2207095270511f4a51ed889514c3899b30492656b2138c24088c`

## Validation

- portable Go core tests: PASS
- Steam -> Steam_current: PASS
- NoSteam 16232 -> dedicated payload: PASS
- newer NoSteam -> Steam_current: PASS
- no-backup policy: PASS
- legacy CI_Mod_Menu_P.* cleanup: implemented
- localization payload names absent from EXE: PASS
- Game.locres / pakchunk1015 / RussianTranslation_P absent from EXE: PASS
- Windows runtime test of this exact EXE: pending user test
