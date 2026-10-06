# CI Mod Menu Modern Installer 2.0

Target: Windows x64. Mod version: 1.1.1. Author: Don't Look.

This installer is only for CI Mod Menu. It does not contain or modify the Russian localization, Game.locres, pakchunk1015-* or RussianTranslation_P.

## Runtime-hang fix

- No Steam-library or game-path scan runs during WM_CREATE/startup.
- Install/update runs on a worker goroutine and posts progress to the Win32 UI.
- Removal runs on a worker goroutine.
- COM is initialized STA before the system folder picker is used with BIF_NEWDIALOGSTYLE.
- The UI message loop stays free during file copy/hash verification.

## UI 2.0

- Native dark Win32 UI.
- DWM immersive dark mode.
- Rounded Windows 11 corners and Mica where supported.
- Cyan accent and owner-drawn buttons.
- Thematic CI Mod Menu icon.
- Separate Steam and NoSteam cards with independent game folders.

## Editions

- Steam: verified game version 0.7.9.16321.
- NoSteam: verified baseline 0.7.9.16232.

## Update semantics

Before every install, delete only:
- CI_ModMenu_P.*
- CI_Mod_Menu_P.*

No backups are created. Then the selected edition payload is written and SHA-256 verified.

## Source

Canonical Installer 2.0 development archive:
- CI GPT/Working/CI_Mod_Menu_v1.1.1_Installer_v2_DEVELOPMENT.zip
- Drive id: 17Zp64Rg4g_IPOEjsMJWqTBZ8uQRWQ5AM
- SHA-256: 50e9c5ddb679e39bb1c9da17cc1628ef87a6e4a6abdc4b385ce29ce28187b946
- main.go SHA-256: 4cc0be346da7c0cf8bae86f0e9a7bcbbf444b9b9f997ca14335c89debd9250da

The archive contains main.go, go.mod, app.manifest, payloads, icon, build notes, static validator and the constrained-environment PE resource patcher.

## Release

CI GPT/Releases/CI_Mod_Menu_v1.1.1_Setup_Modern_Package.zip
- Drive id: 1OTAAYVPiy9bf5ByZVWWtytS2gA4qVGcE
- SHA-256: 8a0dae731da74d2c304a3aedbea6c6bff25e6b137049b622eb3118d2b4a89f24

Installer EXE:
- CI_Mod_Menu_v1.1.1_Setup_Modern.exe
- SHA-256: 2e40d9660f72720b0eaca3c7df7bf8a4fd47525f7ab145572feb660e4a16fada

Windows runtime test of Installer 2.0 is still pending user validation.
