"""Package verified v18.4 outputs without old diagnostic binaries or caches.

Usage: python package_release.py WORKSPACE STAGING ZIP_PATH
Run build.py, validate.py and the Windows installer build first.
"""
from pathlib import Path
import sys, shutil, json, hashlib, zipfile, csv
from datetime import datetime, timezone

work, stage, archive = map(Path, sys.argv[1:4])
repo = Path(__file__).resolve().parents[2]
assert stage != work and not stage.exists(), "Use a fresh staging directory"
now = datetime.now(timezone.utc).isoformat()
stage.mkdir(parents=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


for name in ("Branding", "Data", "Files", "Installer"):
    shutil.copytree(work / name, stage / name)

# Keep historical tooling as text, rather than distribute obsolete game packages.
text_extensions = {".py", ".json", ".md", ".txt", ".tsv", ".go", ".mod"}
for source in (work / "Developer").rglob("*"):
    relative = source.relative_to(work / "Developer")
    if not source.is_file() or source.suffix not in text_extensions:
        continue
    if any(p in {"__pycache__", "payload", "Installer_Source", "V18_4"} for p in relative.parts):
        continue
    target = stage / "Developer" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

installer_sources = stage / "Developer/Installer_Source"
installer_sources.mkdir(parents=True)
for source in (repo / "installer").iterdir():
    if source.is_file() and source.suffix in text_extensions:
        shutil.copy2(source, installer_sources / source.name)
shutil.copy2(repo / "installer/LICENSE_RU.txt", stage / "LICENSE_RU.txt")
tool_destination = stage / "Developer/V18_4/tools"
tool_destination.mkdir(parents=True)
for source in Path(__file__).parent.iterdir():
    if source.is_file() and source.suffix in {".py", ".json"}:
        shutil.copy2(source, tool_destination / source.name)

reports = stage / "Reports"
reports.mkdir()
history = reports / "Historical_Pre18_4"
shutil.copytree(work / "Reports", history)
for name in ("V18_4_DISPLAY_LAYOUT.json", "V18_4_VALIDATION.json"):
    shutil.copy2(work / "Reports" / name, reports / name)
    (history / name).unlink()
source_state = repo / "working/steam/current/full_ui_translation_v18_4/SOURCE_READBACK.json"
shutil.copy2(source_state, reports / "SOURCE_READBACK.json")
validation = json.loads((reports / "V18_4_VALIDATION.json").read_text())
exe = stage / "Installer/CarnalInstinct_RU_Setup.exe"
exe_bytes = exe.read_bytes()
manifest = {
    "schema_version": "1.0", "release": "v18.4 Full UI TEST", "author": "Don't Look",
    "created_at": now, "steam_verified_game_version": "0.7.9.16321",
    "steam_verified_build": None, "nosteam_verified_build": "0.7.9.16232",
    "runtime_tested": False, "installer_mode": "delete_and_replace_without_backups",
    "installer_sha256": digest(exe), "installer_bytes": len(exe_bytes), "payloads": {},
}
for edition, result in validation["editions"].items():
    folder = stage / "Files" / edition
    files = sorted(folder.iterdir())
    assert {f.name for f in files} == {"pakchunk1015-Windows_P." + ext for ext in ("pak", "utoc", "ucas")}
    for source in files:
        assert source.read_bytes() in exe_bytes, "Installer does not embed this exact payload"
    manifest["payloads"][edition] = {
        "packages": result["packages"], "translation_rows": result["translation_rows"],
        "locres_entries": result["locres_entries"],
        "files": [{"path": str(f.relative_to(stage)), "bytes": f.stat().st_size, "sha256": digest(f)} for f in files],
    }
save(reports / "RUNTIME_PAYLOAD_MANIFEST.json", manifest)
save(reports / "BUILD_VALIDATION.json", {
    "release": "v18.4", "status": "static_validation_pass_runtime_pending", "runtime_tested": False,
    "resource_validation": validation, "installer_go_tests_and_race_detector": "PASS",
    "installer_go_vet": "PASS", "installer_windows_amd64_build": "PASS",
    "installer_exact_embedded_payload_readback": "PASS", "installer_sha256": digest(exe),
})
save(reports / "AUDIT_STATE.json", {
    "schema_version": "1.0", "release": "v18.4", "status": "static_complete_runtime_pending",
    "last_completed_unit": "both_edition_payloads_and_replace_installer_verified",
    "next_unit": "startup_and_visual_validation_in_both_game_editions", "runtime_tested": False,
    "steam_state_path": "working/steam/current/full_ui_translation_v18_4/AUDIT_STATE.json",
    "nosteam_state_path": "working/nosteam/0.7.9.16232/full_ui_translation_v18_4/AUDIT_STATE.json",
})

readme = """# Carnal Instinct — русификация 18.4 TEST

Автор: **Don't Look**. Основа: 18.3.

Меню персонажа и журнал восстановлены по предоставленным скринам в **обоих комплектах**. Расширены области характеристик, настроены переносы и читаемый прямой шрифт журнала. Исправлены надписи и отступы кнопок настроек. Проверены переводы найденных подписей карты и миникарты, исправлены подписи порта/IP и конфликт перевода малого сгустка эссенции.

## Установка

1. Закройте игру и распакуйте архив.
2. Запустите `Installer/CarnalInstinct_RU_Setup.exe`.
3. Выберите свою версию и папку игры, затем выполните установку.

Steam: проверенные исходники **0.7.9.16321**. NoSteam: отдельный комплект **0.7.9.16232**. Вариант NoSteam 0.7.9.16313 / 16315+ использует комплект Steam_current, как в 18.3; совместимость с каждой более новой сборкой требует проверки.

Установщик заменяет старые файлы перевода без создания бэкапов и очищает старые резервные копии этого русификатора. Удаление русификации не восстанавливает предыдущий перевод. Посторонние моды, сохранения и настройки игры не входят в очистку.

## Проверка сборки

Проверены контейнеры обеих версий, ключи и исходные хеши текстов, подстановки, параметры интерфейса и установщик. Код функций игровых виджетов сохранён. Подробности — `Reports/V18_4_VALIDATION.json` и `Reports/BUILD_VALIDATION.json`.

**18.4 ещё не запускалась в игре.** После установки нужно проверить запуск, меню персонажа, журнал с длинными заданиями, кнопки настроек и наведение на метки карты/миникарты при используемом разрешении и масштабе интерфейса. Затем — загрузку сохранения, управление, бой и выполнение задания. До этой проверки сборка обозначена TEST.
"""
(stage / "README_RU.md").write_text(readme, encoding="utf-8")
changelog = """# 18.4 TEST — 5 октября 2026

- В обоих комплектах восстановлены широкие меню персонажа и журнал по скринам; изменены ширина строк характеристик, переносы, размер и начертание текста журнала.
- Исправлены подписи порта и IP, сокращены кнопки обновления/сброса; в Steam добавлены отступы и перенос текста кнопок настроек.
- Проверены 3263 вхождения текста меток Steam и 3103 NoSteam: отсутствующих переводов в проверенных виджетах нет.
- В Steam исправлен конфликт трёх подписей малого сгустка эссенции только на уровне отображаемого текста.
- Установщик удаляет и заменяет перевод без бэкапов; очищает его старые резервные копии, сохраняет посторонние файлы.
- 31 пакет Steam и 71 пакет NoSteam прошли чтение контейнеров; исходные ключи, хеши и подстановки проверены. Байты существующих функций сохранены.
- Полный аварийный override quest_objectives из прежних сборок исключён; минимальный вариант 18.3 сохранён.
- Проверка запуска, внешнего вида и игровой механики в самой игре ещё не выполнена.

## История до 18.4

"""
(stage / "CHANGELOG_RU.md").write_text(changelog + (work / "CHANGELOG_RU.md").read_text(), encoding="utf-8")
(stage / "Developer/V18_4/README.md").write_text("""# Rebuild and independent validation

Keep the immutable verified v18.3 archive (SHA256 acb8b64ddd4caece240e29b6deae0e1aafe6d8d501578fa1bfe924d128c79b5b) as BASE. Copy its canonical tree to WORK. Fetch current Steam source files identified by Reports/SOURCE_READBACK.json to SOURCE; verify their hashes before using them. Original game sources remain read-only.

With Python 3, set CI_RU_RELEASE_WORKSPACE to WORK, then run:

    python tools/build.py WORK SOURCE BASE
    python tools/validate.py WORK BASE SOURCE

The tools use the native UMG schema included here and the pure Python helpers in Developer/MapFix and Developer/SafeUIFix/tools. Cooked inputs and old diagnostic payloads are deliberately excluded from this distribution; BASE is required for a reproducible rebuild.

For the installer, run Developer/Installer_Source/build.py with --files WORK/Files, --icon WORK/Branding/ci_ru.ico, --go PATH_TO_GO and --output WORK/Installer/CarnalInstinct_RU_Setup.exe. It creates its embedded payload from these exact files. Run its core tests with core.go, core_test.go and no_backup_test.go, including the race detector on a supported host. The installer targets Windows amd64; it was cross-compiled, not launched in Windows.

Historical tools and reports are reference material. Current results are Reports/V18_4_VALIDATION.json and Reports/BUILD_VALIDATION.json. Static validation does not substitute for playing either game edition.
""", encoding="utf-8")

files = sorted(p for p in stage.rglob("*") if p.is_file())
sums = "".join(f"{digest(p)}  {p.relative_to(stage).as_posix()}\n" for p in files)
(stage / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
files.append(stage / "SHA256SUMS.txt")
archive.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for path in sorted(files):
        z.write(path, path.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == len(set(z.namelist())) == len(files)
    for path in files:
        assert z.read(path.relative_to(stage).as_posix()) == path.read_bytes()
    assert not any(n.startswith(("Diagnostics/", "Extracted/", "VerifiedExtracted/")) or "__pycache__" in n for n in z.namelist())
report = {
    "release": "v18.4 Full UI TEST", "name": archive.name, "created_at": now,
    "sha256": digest(archive), "archive_bytes": archive.stat().st_size, "archive_entries": len(files),
    "zip_crc": "PASS", "all_entries_byte_readback": "PASS", "runtime_tested": False,
    "installer_sha256": digest(exe), "installer_bytes": len(exe_bytes),
    "steam_packages": 31, "nosteam_packages": 71,
    "drive_upload": "pending",
}
save(archive.with_suffix(".json"), report)
save(repo / "working/steam/current/full_ui_translation_v18_4/FINAL_ARCHIVE_VALIDATION.json", report)
print(json.dumps(report, ensure_ascii=False, indent=2))
