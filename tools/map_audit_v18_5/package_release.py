"""Package v18.5 without source assets, stale caches or obsolete binaries."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, sys, zipfile

work, stage, archive = map(Path, sys.argv[1:4])
repo = Path(__file__).resolve().parents[2]
assert not stage.exists() and not archive.exists()
stage.mkdir(parents=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
def copy(p, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)

for name in ('Branding', 'Data', 'Files', 'Installer'):
    shutil.copytree(work / name, stage / name)
for path in (repo / 'installer').iterdir():
    if path.is_file() and path.suffix in ('.go', '.py', '.json', '.mod', '.txt'):
        copy(path, stage / 'Developer/Installer_Source' / path.name)
for folder in ('map_audit_v18_5', 'ui_translation_v18_4'):
    for path in (repo / 'tools' / folder).iterdir():
        if path.is_file() and path.suffix in ('.py', '.json', '.go'):
            copy(path, stage / 'tools' / folder / path.name)
for name in ('ci_formats.py', 'cityhash_pure.py', 'pure_blake3.py'):
    copy(work / 'Developer/SafeUIFix/tools' / name, stage / 'Developer/SafeUIFix/tools' / name)
copy(work / 'Developer/MapFix/zen.py', stage / 'Developer/MapFix/zen.py')
for name in ('iostore_simple.py', 'blake3_pure.py'):
    copy(work / 'Developer/AnimationIsolationFix' / name, stage / 'Developer/AnimationIsolationFix' / name)
copy(repo / 'installer/LICENSE_RU.txt', stage / 'LICENSE_RU.txt')
reports = stage / 'Reports'; reports.mkdir()
for name in ('V18_5_RADIAL_SETTINGS.json', 'V18_5_MAP_DISPLAY_ALIASES.json', 'V18_5_TRANSLATION_MAP_AUDIT.json',
             'V18_5_VALIDATION.json', 'V18_5_STARTUP_PROBE.json', 'V18_5_INDEPENDENT_CONTAINER_VALIDATION.json'):
    copy(work / 'Reports' / name, reports / name)
state_dir = repo / 'working/steam/current/crash_map_radial_grammar_v18_5'
for name in ('CRASH_ANALYSIS.json', 'FULL_MAP_SOURCE_AUDIT.json'):
    copy(state_dir / name, reports / name)
copy(repo / 'steam/current/BUILD_STATE.json', reports / 'STEAM_SOURCE_BUILD_STATE.json')
copy(work / 'Reports/V18_4_VALIDATION.json', reports / 'Historical_Pre18_5/V18_4_STATIC_VALIDATION.json')
validation = json.loads((reports / 'V18_5_VALIDATION.json').read_text())
exe = stage / 'Installer/CarnalInstinct_RU_Setup.exe'; exe_bytes = exe.read_bytes()
manifest = {'release': 'v18.5 TEST', 'created_at': datetime.now(timezone.utc).isoformat(),
            'author': "Don't Look", 'runtime_tested': False, 'steam_crash_root_cause': 'unconfirmed',
            'steam_verified_source_version': '0.7.9.16321', 'steam_installed_build': None,
            'nosteam_fixed_source_build': '0.7.9.16232', 'installer_mode': 'delete_and_replace_without_backups',
            'installer_sha256': sha(exe), 'installer_bytes': len(exe_bytes), 'payloads': {}}
for edition, result in validation['editions'].items():
    paths = sorted((stage / 'Files' / edition).iterdir())
    assert {p.name for p in paths} == {'pakchunk1015-Windows_P.' + e for e in ('pak', 'utoc', 'ucas')}
    assert all(p.read_bytes() in exe_bytes for p in paths), 'stale installer payload'
    manifest['payloads'][edition] = {**result, 'files': [{'path': p.relative_to(stage).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in paths]}
save(reports / 'RUNTIME_PAYLOAD_MANIFEST.json', manifest)
save(reports / 'BUILD_VALIDATION.json', {'release': '18.5 TEST', 'runtime_tested': False,
     'static_status': 'PASS', 'display_regressions': '8/8 PASS from final cooked payload',
     'installer_core_tests_with_race_detector': 'PASS', 'installer_core_go_vet': 'PASS',
     'windows_amd64_build': 'PASS; not launched in Windows', 'exact_six_embedded_payloads': 'PASS',
     'steam_startup_crash_fixed': 'not established', 'settings_fps_and_visual_fit': 'runtime pending',
     'full_human_dialogue_proofread': 'not completed'})
save(reports / 'AUDIT_STATE.json', {'release': '18.5 TEST', 'status': 'static_verified_runtime_and_editorial_work_pending',
     'last_completed_unit': 'payload_installer_and_startup_probe_static_checks',
     'next_unit': 'in_game_startup_probe_then_visual_performance_and_remaining_dialogue_review',
     'runtime_tested': False})
readme = '''# Carnal Instinct — русификация 18.5 TEST

Автор: Don't Look. Два отдельных комплекта Steam и NoSteam, основа 18.4.

В радиальном меню подписи перенесены ниже значков, добавлен перенос строк; размер области выбора сохранён. При открытии настроек убрано повторное применение сохранённых параметров. Ручные кнопки применения и сохранения настроек сохранены.

Исправлен неверный переход обработчика ухода курсора с метки карты. Добавлены варианты написания Tal'Senet / Tal’Senet и SearchArea для существующих переводов. Проверены все 2513 файла карт актуального источника Steam: найденные 181 уникальный ключ обычного FText уже есть в обеих таблицах перевода. Это проверка файлов данного источника; созданные во время игры подписи и карты отдельной сборки NoSteam ещё требуют проверки в игре. Технические имена акторов, заданий и сохранений не переводились.

Внесена 131 адресная правка текста: 72 Steam, 59 NoSteam. Исправлены согласование, отдельные реплики, названия и терминология; приведено к одному написанию Маз-Арджени в заданиях и на карте. Все 41133 строки проверены на целостность ключей, английских хешей, подстановок, тегов и переносов. Полная ручная вычитка всех диалогов пока не завершена.

Широкие меню персонажа и журнал из 18.4 сохранены. Их окончательный внешний вид при разных разрешениях ещё нужно проверить в игре.

## Установка

1. Закройте игру и распакуйте весь архив.
2. Запустите Installer/CarnalInstinct_RU_Setup.exe.
3. Выберите свою версию и папку игры.

Steam: исходники проверены как 0.7.9.16321; точная установленная сборка пользователя неизвестна. NoSteam: отдельный комплект 0.7.9.16232. Вариант NoSteam 0.7.9.16313 / 16315+ использует Steam_current, как прежде; совместимость с этими сборками отдельно не подтверждена.

Установщик удаляет и заменяет файлы русификатора без создания бэкапов. Старые резервные копии именно этого русификатора очищаются; посторонние моды и сохранения не входят в очистку. При удалении предыдущий перевод не восстанавливается.

## Что ещё не подтверждено

Steam 18.4 падала при запуске в FAsyncLoadingThread. В предоставленном дампе нет имени повреждённого ресурса. Причина этого краша пока не установлена, поэтому запуск Steam 18.5 нельзя считать исправленным. Для поиска причины подготовлен отдельный архив Carnal_Instinct_RU_Steam_Startup_Probe_v18.5.zip: крайние варианты точно воспроизводят файлы 18.3 и 18.4, изменения включаются по одному. В нём есть инструкции и отдельная программа установки диагностических наборов.

18.5 ещё не запускалась в игре. Статические проверки контейнеров, локализации и функций проходят, 8 проверок исправлений проходят; установщик проверен тестами и собран для Windows amd64. Это не подтверждает отсутствие краша, улучшение FPS настроек или размещение всех надписей на экране. После проверки запуска нужны меню персонажа, длинные задания в журнале, настройки, радиальное меню, подсказки карты/миникарты и загрузка сохранения с выполнением задания.

Текущие результаты — Reports/V18_5_VALIDATION.json и Reports/BUILD_VALIDATION.json. Исторические отчёты отдельно помечены.
'''
(stage / 'README_RU.md').write_text(readme)
(stage / 'CHANGELOG_RU.md').write_text('''# 18.5 TEST — 5 октября 2026

- Подписи радиального меню ниже значков, с переносом; область выбора сохранена.
- Открытие настроек больше не вызывает повторное применение параметров через SettingsMenu.Activate.
- Исправлен переход OnMouseLeave метки карты в данные строки вместо инструкции очистки подсказки.
- Добавлены три варианта входных названий для существующих переводов карты; проверены 2513 файлов карт Steam.
- 131 правка перевода с сохранением исходных ключей, хешей, подстановок и переносов.
- Широкие меню персонажа и журнал сохранены в обоих комплектах.
- 34 пакета Steam и 71 NoSteam проверены чтением; 94 функции изменённых виджетов прошли строгую проверку сериализации и переходов; 8 проверок исправлений PASS.
- Новый установщик содержит именно файлы 18.5, заменяет перевод без бэкапов.
- Отдельный диагностический комплект из 10 вариантов воспроизводит изменения Steam 18.3 → 18.4 по одному.
- Причина краша Steam при запуске ещё не подтверждена. Проверки FPS и внешнего вида в игре, а также полная ручная вычитка диалогов остаются незавершёнными.
''')
(stage / 'Developer/README.md').write_text('''# Rebuild

Use immutable verified v18.4 as BASE (SHA256 b801a03e6027812f1434bfda822fe4cd5124f8202dd3f9f1a809be634e7cb0ca), v18.3 for the probe (SHA256 acb8b64ddd4caece240e29b6deae0e1aafe6d8d501578fa1bfe924d128c79b5b), and matching current Steam source assets. Sources and cooked input caches are deliberately excluded. Read Reports/FULL_MAP_SOURCE_AUDIT.json for source hashes and method limits.

Set CI_RU_RELEASE_WORKSPACE to this release tree, providing the included Python helpers. Extract BASE's Files containers to BASE/VerifiedExtracted before patching; do not use copied stale Extracted caches. Run tools/map_audit_v18_5/patch_ui.py WORK BASE SOURCE, patch_map_aliases.py WORK BASE SOURCE FULL_MAP_SCAN, update_translation.py WORK BASE FULL_MAP_SCAN, then build_payload.py WORK BASE SOURCE. Use a fresh WORK/FinalExtracted for final readback. Run test_display_regressions.py with CI_RU_CHECK_ROOT=WORK. FULL_MAP_SCAN can be recreated using scan_map_sources.py and verified source files.

Build the installer using Developer/Installer_Source/build.py with --files WORK/Files, --icon WORK/Branding/ci_ru.ico, --go PATH_TO_GO and --output WORK/Installer/CarnalInstinct_RU_Setup.exe. Go core tests include no_backup_test.go and race detection. The Windows binary was cross-compiled, not launched in Windows. probe_main.go reuses the same installer core for its separate diagnostic archive; build_startup_probe.py verifies all stages and exact failed-release reproduction.

Runtime checks remain pending. Do not label this release FINAL or infer a Steam crash fix from static parsing.
''')
files = sorted(p for p in stage.rglob('*') if p.is_file())
(stage / 'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files))
files.append(stage / 'SHA256SUMS.txt')
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(files): z.write(p, p.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert not z.testzip()
    assert len(z.namelist()) == len(set(z.namelist())) == len(files)
    for p in files: assert z.read(p.relative_to(stage).as_posix()) == p.read_bytes()
    assert not any('__pycache__' in n or '/patched/' in n or n.startswith(('Extracted/', 'FinalExtracted/', 'Diagnostics/')) for n in z.namelist())
report = {'release': 'v18.5 TEST', 'name': archive.name, 'sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
          'archive_entries': len(files), 'zip_crc': 'PASS', 'every_archive_entry_readback': 'PASS',
          'exact_installer_payload': 'PASS', 'installer_sha256': sha(exe), 'runtime_tested': False,
          'steam_crash_root_cause': 'unconfirmed', 'drive_upload': 'pending'}
save(archive.with_suffix('.json'), report)
print(json.dumps(report, ensure_ascii=False, indent=2))
