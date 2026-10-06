# CI Mod Menu installer build

Target: Windows x64. Installer version: 1.1.1. Author: Don't Look.

The installer contains only `CI_ModMenu_P.pak/.utoc/.ucas`. It does not contain or modify the Russian localization, `Game.locres`, `pakchunk1015-*`, or `RussianTranslation_P`.

## Payload layout

- `payload/steam/` — Steam payload, verified with 0.7.9.16321.
- `payload/nosteam/` — NoSteam payload, verified with 0.7.9.16232.

Both directories are deliberately kept separate even when their current bytes are identical.

## Update semantics

Before every installation, all files matching `CI_ModMenu_P.*` and legacy `CI_Mod_Menu_P.*` in the selected game's `Content/Paks` are deleted. No backups are created. Then the selected edition payload is written and SHA-256 verified from the embedded data.

## Source restoration

`main.go.gz.b64` is the gzip-compressed, base64-encoded canonical `main.go`. Run `restore_main_source.py` to restore it. Restored `main.go` SHA-256 must be:

`825139bfc2a54648a1f406261d47d60815a26879b2cb6d67310653f45f8a9741`

## Build

1. Install Go 1.23+.
2. Install `github.com/akavel/rsrc` v0.10.2.
3. Restore `main.go`.
4. Generate `assets/ci_mod_menu.ico` with `icon_generator.py`.
5. Put the three mod container files in each payload directory.
6. Run:

```bash
rsrc -arch amd64 -ico assets/ci_mod_menu.ico -manifest app.manifest -o rsrc_windows_amd64.syso
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags="-H windowsgui -s -w" -o CI_Mod_Menu_v1.1.1_Setup.exe .
```

The manifest requests administrator rights so installation under Program Files works.
