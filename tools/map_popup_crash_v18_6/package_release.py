"""Clean v18.6 deliverable, with exact installer payload and archive readback."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, sys, zipfile

work, stage, archive = map(Path, sys.argv[1:4])
repo = Path(__file__).resolve().parents[2]
assert not stage.exists() and not archive.exists()
stage.mkdir(parents=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def copy(path, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)

for name in ('Branding', 'Data', 'Files', 'Installer'):
    shutil.copytree(work / name, stage / name)
for path in (repo / 'installer').iterdir():
    if path.is_file() and path.suffix in ('.go', '.py', '.json', '.mod', '.txt'):
        copy(path, stage / 'Developer/Installer_Source' / path.name)
for folder in ('map_popup_crash_v18_6', 'map_audit_v18_5', 'ui_translation_v18_4'):
    for path in (repo / 'tools' / folder).iterdir():
        if path.is_file() and path.suffix in ('.py', '.json', '.go'):
            copy(path, stage / 'tools' / folder / path.name)
copy(repo / 'tools/native_ftext.py', stage / 'tools/native_ftext.py')
for name in ('ci_formats.py', 'cityhash_pure.py', 'pure_blake3.py'):
    copy(work / 'Developer/SafeUIFix/tools' / name, stage / 'Developer/SafeUIFix/tools' / name)
copy(work / 'Developer/MapFix/zen.py', stage / 'Developer/MapFix/zen.py')
for name in ('iostore_simple.py', 'blake3_pure.py'):
    copy(work / 'Developer/AnimationIsolationFix' / name, stage / 'Developer/AnimationIsolationFix' / name)
copy(repo / 'installer/LICENSE_RU.txt', stage / 'LICENSE_RU.txt')
for path in (work / 'Reports').glob('V18_6_*.json'):
    copy(path, stage / 'Reports' / path.name)
for name in ('V18_5_RADIAL_SETTINGS.json', 'V18_5_TRANSLATION_MAP_AUDIT.json', 'FULL_MAP_SOURCE_AUDIT.json'):
    copy(work / 'Reports' / name, stage / 'Reports/Historical_v18_5' / name)
copy(repo / 'steam/current/BUILD_STATE.json', stage / 'Reports/STEAM_SOURCE_BUILD_STATE.json')

validation = json.loads((work / 'Reports/V18_6_VALIDATION.json').read_text())
exe = stage / 'Installer/CarnalInstinct_RU_Setup.exe'
exe_bytes = exe.read_bytes()
trusted = json.loads((repo / 'installer/trusted_hashes.json').read_text())
manifest = {'release': 'v18.6 TEST', 'created_at': datetime.now(timezone.utc).isoformat(), 'author': "Don't Look",
            'runtime_tested': False, 'steam_verified_source_version': '0.7.9.16321', 'steam_installed_build': None,
            'nosteam_fixed_source_build': '0.7.9.16232', 'installer_mode': 'delete_and_replace_without_backups',
            'installer_sha256': sha(exe), 'installer_bytes': len(exe_bytes), 'payloads': {}}
for edition, result in validation['editions'].items():
    paths = sorted((stage / 'Files' / edition).iterdir())
    assert {p.name for p in paths} == {'pakchunk1015-Windows_P.' + ext for ext in ('pak', 'utoc', 'ucas')}
    assert all(p.read_bytes() in exe_bytes and sha(p) in trusted[p.name] for p in paths), 'stale/untrusted installer payload'
    manifest['payloads'][edition] = {**result, 'files': [{'path': p.relative_to(stage).as_posix(),
                                                      'bytes': p.stat().st_size, 'sha256': sha(p)} for p in paths]}
save(stage / 'Reports/RUNTIME_PAYLOAD_MANIFEST.json', manifest)
save(stage / 'Reports/BUILD_VALIDATION.json', {
    'release': '18.6 TEST', 'runtime_tested': False, 'static_status': 'PASS',
    'regression_tests_from_final_payload': '11/11 PASS', 'translated_caption_cases_checked': 12586,
    'installer_core_tests_with_race_detector': 'PASS', 'windows_amd64_build': 'PASS; not launched in Windows',
    'exact_six_embedded_and_trusted_payloads': 'PASS',
    'crash_cause': 'Invalid native Namespace FString count in Essence, proven and corrected; runtime retest pending',
    'settings_fps_visual_fit': 'runtime pending', 'full_manual_dialogue_proofread': 'unfinished'})
save(stage / 'Reports/AUDIT_STATE.json', {'release': '18.6 TEST', 'status': 'static_verified_runtime_and_editorial_work_pending',
    'last_completed_unit': 'corrected_payload_installer_static_checks',
    'next_unit': 'in_game_startup_settings_caption_retest_then_remaining_dialogue_review', 'runtime_tested': False})

(stage / 'README_RU.md').write_text('''# Carnal Instinct — русификатор 18.6 TEST

Автор: Don't Look. В архиве отдельные комплекты Steam и NoSteam и общий установщик.

## Изменения

- Исправлены повреждённые записи текста в Essence_Tier_1_Small — единственном добавлении в падающей пробе 9. Названия и описания переводятся; остальные данные предмета сохранены.
- Верхняя и нижняя строки подсказки карты и пять путей вывода текста значков используют общий словарь из 899 известных подписей. Добавлены «Ракоте», «Житница», «Лагерь анубитов» и другие пропущенные названия. Перевод известных подписей работает независимо от момента их появления при прохождении.
- В обоих комплектах сохранено исправление открытия настроек из 18.5: сохранённые параметры не применяются повторно при каждом открытии. Работа кнопок применения и сохранения сохранена. Старые пробы 0–9 использовали меню 18.3.
- Сохранены широкие меню персонажа и журнал, подписи радиального меню под значками, 131 предыдущая адресная правка текста.
- Идентификаторы акторов, предметов, заданий и сохранений не переводились.

## Установка

1. Закройте игру и распакуйте архив.
2. Запустите Installer/CarnalInstinct_RU_Setup.exe.
3. Выберите свою версию и папку игры.

Установщик заменяет файлы русификатора без создания бэкапов и очищает старые резервные копии этого русификатора. Посторонние моды и сохранения не входят в очистку.

Исходная версия Steam проверена как 0.7.9.16321; точный установленный BuildID пользователя неизвестен. Отдельный комплект NoSteam рассчитан на 0.7.9.16232. Вариант NoSteam 0.7.9.16313/16315+ использует Steam_current; отдельная проверка совместимости этих сборок не проводилась.

## Проверка

Пройдены 11 проверок исправлений, чтение обоих контейнеров, проверка всех 12 586 записей словарей карты по исходному тексту и хешу, 41 137 строк таблиц перевода. Установщик собран для Windows и содержит именно шесть новых файлов этой версии; его логика замены без бэкапов проверена тестами с обнаружением гонок.

18.6 ещё не запускалась в игре. Требуют проверки: запуск Steam после исправления эссенции, плавность настроек, обе строки подсказок карты и миникарты, внешний вид меню персонажа, журнала и радиального меню. Полная ручная вычитка всех диалогов ещё не завершена. Неизвестные подписи из других сборок не покрываются автоматически.

Текущие отчёты находятся в Reports/V18_6_*.json. Отчёты предыдущей версии находятся отдельно в Reports/Historical_v18_5.
''')
(stage / 'CHANGELOG_RU.md').write_text('''# 18.6 TEST

- Steam: исправлена сериализация трёх записей FText предмета Essence_Tier_1_Small; устранена длина строки, выходившая за пределы экспортируемого объекта. Остальные данные предмета побайтно сохранены.
- Обе версии: 899 известных подписей подключены к обеим строкам всплывающей подсказки и всем пяти веткам вывода текста значков карты. Добавлены Raqote → Ракоте, The Breadbasket → Житница, Anubite Camp → Лагерь анубитов.
- Все другие пакеты 18.5 сохранены, включая широкие меню персонажа/журнала, настройки и радиальное меню. Установщик обновлён и содержит новые комплекты.
- 11 проверок PASS, все 12 586 записей словарей карты находят перевод. Исправленная версия требует проверки в игре; полная ручная вычитка диалогов остаётся незавершённой.
''')
(stage / 'Developer/README.md').write_text('''# Rebuild 18.6

Use the verified v18.5 archive (SHA256 0cd44ce3ab351b2b85a7fd0efbf45339a510b8184fa3d6b87423f5cfb2b323ef) as immutable BASE. Extract BASE Files containers freshly into BASE/FinalExtracted. Never use stale copied Extracted caches.

Set CI_RU_RELEASE_WORKSPACE to the release tree to locate included helpers. Start WORK as a clean copy of BASE. From the matching immutable Steam source, run tools/map_popup_crash_v18_6/fix_native_item.py WORK SOURCE. Source is the Content parent. Run patch_captions.py WORK BASE FULL_MAP_SCAN.json, then build_payload.py WORK BASE. Recreate FULL_MAP_SCAN.json using tools/map_audit_v18_5/scan_map_sources.py and all 2513 verified shipping-map source files. Cooked inputs and source cache are deliberately excluded from this archive.

Run unittest discover -s tools/map_popup_crash_v18_6 -p 'test_*.py' with CI_RU_CHECK_ROOT=WORK, then tools/map_audit_v18_5/test_display_regressions.py. The latter verifies both-edition retained radial layout, main-menu settings activation, map OnMouseLeave targets and apostrophe aliases. verify_containers.py reads the final WORK/Files independently; its historical default report name says V18_5 and must be relabeled 18.6 when used on WORK.

Build using Developer/Installer_Source/build.py --files WORK/Files --icon WORK/Branding/ci_ru.ico --go PATH_TO_GO --output WORK/Installer/CarnalInstinct_RU_Setup.exe. Run core.go/core_test.go/no_backup_test.go with Go test -race. package_release.py WORK STAGE ARCHIVE builds a clean archive, verifies all six embedded/trusted files and every ZIP entry.

The native FText fix reads and writes the whole Base history record. Empty Namespace FString can occupy four or five bytes. Never match a four-byte empty FString inside a five-byte field. Preserve original flags/key/source and every byte outside the text records.

Runtime startup/settings FPS/layout checks and remaining dialogue review are pending. NoSteam has no Essence class override. Do not alter Neutral_Widget, gameplay IDs or the minimal quest-objectives override based on this patch.
''')

files = sorted(p for p in stage.rglob('*') if p.is_file())
(stage / 'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files))
files.append(stage / 'SHA256SUMS.txt')
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(files): z.write(p, p.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert not z.testzip() and len(z.namelist()) == len(set(z.namelist())) == len(files)
    assert all(z.read(p.relative_to(stage).as_posix()) == p.read_bytes() for p in files)
    assert not any('__pycache__' in n or '/patched/' in n or n.startswith(('Extracted/', 'FinalExtracted/')) for n in z.namelist())
report = {'release': 'v18.6 TEST', 'name': archive.name, 'sha256': sha(archive),
          'archive_bytes': archive.stat().st_size, 'archive_entries': len(files), 'zip_crc_and_exact_entry_readback': 'PASS',
          'installer_sha256': sha(exe), 'exact_installer_payload': 'PASS', 'runtime_tested': False, 'drive_upload': 'pending'}
save(archive.with_suffix('.json'), report)
print(json.dumps(report, ensure_ascii=False, indent=2))
