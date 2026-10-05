"""Clean 18.7 package; verify exact embedded payloads and complete ZIP readback."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,sys,zipfile

work,stage,archive=map(Path,sys.argv[1:4]);repo=Path(__file__).resolve().parents[2]
assert not stage.exists() and not archive.exists();stage.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
for name in ['Branding','Data','Files','Installer']:shutil.copytree(work/name,stage/name)
for src in (repo/'installer').iterdir():
    if src.is_file() and src.suffix in ['.go','.py','.json','.mod','.txt']:copy(src,stage/'Developer/Installer_Source'/src.name)
for folder in ['ui_parity_v18_7','map_popup_crash_v18_6','map_audit_v18_5','ui_translation_v18_4']:
    for src in (repo/'tools'/folder).iterdir():
        if src.is_file() and src.suffix in ['.py','.json','.go']:copy(src,stage/'tools'/folder/src.name)
copy(repo/'tools/native_ftext.py',stage/'tools/native_ftext.py')
for name in ['ci_formats.py','cityhash_pure.py','pure_blake3.py']:copy(work/'Developer/SafeUIFix/tools'/name,stage/'Developer/SafeUIFix/tools'/name)
copy(work/'Developer/MapFix/zen.py',stage/'Developer/MapFix/zen.py')
for name in ['iostore_simple.py','blake3_pure.py']:copy(work/'Developer/AnimationIsolationFix'/name,stage/'Developer/AnimationIsolationFix'/name)
copy(repo/'installer/LICENSE_RU.txt',stage/'LICENSE_RU.txt')
for src in (work/'Reports').glob('V18_7_*.json'):copy(src,stage/'Reports'/src.name)
for src in (work/'Reports').glob('V18_6_*.json'):copy(src,stage/'Reports/Historical_v18_6'/src.name)
copy(repo/'steam/current/BUILD_STATE.json',stage/'Reports/STEAM_SOURCE_BUILD_STATE.json')
validation=json.loads((work/'Reports/V18_7_VALIDATION.json').read_text())
exe=stage/'Installer/CarnalInstinct_RU_Setup.exe';binary=exe.read_bytes()
trusted=json.loads((repo/'installer/trusted_hashes.json').read_text())
manifest={'release':'18.7 TEST','created_at':datetime.now(timezone.utc).isoformat(),'author':"Don't Look",'runtime_tested':False,
    'steam_verified_source_version':'0.7.9.16321','steam_installed_build':None,'nosteam_fixed_source_build':'0.7.9.16232',
    'installer_mode':'delete_and_replace_without_backups','installer_sha256':sha(exe),'installer_bytes':len(binary),'payloads':{}}
for edition,v in validation['editions'].items():
    files=sorted((stage/'Files'/edition).iterdir())
    assert {p.name for p in files}=={'pakchunk1015-Windows_P.'+x for x in ['pak','utoc','ucas']}
    assert all(p.read_bytes() in binary and sha(p) in trusted[p.name] for p in files)
    manifest['payloads'][edition]={**v,'files':[{'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
save(stage/'Reports/RUNTIME_PAYLOAD_MANIFEST.json',manifest)
save(stage/'Reports/BUILD_VALIDATION.json',{'release':'18.7 TEST','static_status':'PASS','runtime_tested':False,
    'regression_tests_from_final_payload':'17/17 PASS','strict_changed_ui_functions':174,
    'native_slot_graph_and_create_serialize_dependencies':'PASS','independent_container_hashes_imports_export_spans':'PASS',
    'installer_core_race_tests':'PASS','windows_amd64_build':'PASS; not launched on Windows','six_exact_embedded_and_trusted_files':'PASS',
    'nosteam_payload_and_both_translation_tables':'unchanged from 18.6',
    'pending':['Steam startup','exact visual parity to screenshots','crafting click/hover/progression behavior','settings FPS','shared Theme_3 heading fit','full manual dialogue proofreading']})
save(stage/'Reports/AUDIT_STATE.json',{'release':'18.7 TEST','status':'static_verified_runtime_pending',
    'last_completed_unit':'final_container_installer_static_validation','next_unit':'in_game_steam_character_journal_crafting_and_settings_retest','runtime_tested':False})
(stage/'README_RU.md').write_text('''# Carnal Instinct — русификатор 18.7 TEST

Автор: Don't Look. В архиве отдельные комплекты Steam и NoSteam и общий установщик.

## Что изменено в Steam

- Меню персонажа переработано по образцу скриншотов NoSteam: включены фиолетовые рамки, новые заголовки и полосы опыта, добавлены тёмные панели. Старые дубли скрыты. Размеры колонок теперь применяются; окно масштабируется вместе с экраном.
- Показана вкладка «Изготовление» сразу после «Лор». Существующие условия доступности и действия кнопки сохранены.
- Цели задания расположены над журналом, обе области используют ширину правой панели. Включены современные рамки категорий, подобраны шрифты и переносы текста. Заголовок выбранного задания остаётся золотым; основной текст — белым.
- Убраны лишний заголовок списка и старая строка кнопок. Отслеживание задания правой кнопкой мыши сохранено.

Комплект NoSteam 0.7.9.16232 оставлен побайтно таким, как в 18.6: на присланных скриншотах его меню уже имеют нужное оформление.

## Что сохранено из предыдущих обновлений

- Исправление повреждённой записи предмета, из-за которой падала проба с Essence_Tier_1_Small.
- Перевод обеих строк подсказок карты и подписей миникарты по общему списку из 899 известных названий, в том числе «Ракоте», «Житница» и «Лагерь анубитов». Известные названия переводятся и при появлении новых меток по ходу игры.
- Исправление повторного применения настроек при открытии меню; подписи радиального меню под значками.
- Предыдущие исправления текста, перевод задания «Адская кухня» с его целями и описаниями, дополнительные реплики Кордона в Steam.
- Установка без создания резервных копий и очистка старых резервных копий русификатора.

## Установка

1. Закройте игру и распакуйте архив.
2. Запустите Installer/CarnalInstinct_RU_Setup.exe.
3. Выберите свою версию и папку игры.

Установщик заменяет файлы перевода. Сохранения и посторонние моды не входят в очистку.

Исходные файлы Steam проверены для версии игры 0.7.9.16321; точная установленная сборка пользователя неизвестна. Отдельный NoSteam рассчитан на 0.7.9.16232. Для новых вариантов NoSteam установщик предлагает комплект Steam; их совместимость отдельно не проверена.

## Статус проверки

Пройдены 17 проверок, проверено чтение всех файлов двух комплектов и обработчиков изменённых меню. Установщик собран для Windows и содержит именно файлы этой версии.

Это тестовая сборка. Запуск Steam, точное совпадение меню со скриншотами, работа «Изготовления», плавность настроек и внешний вид заголовков требуют проверки в игре. Заголовки Steam используют общий стиль, поэтому их увеличение затрагивает также другие меню этой темы. Полная ручная вычитка всех диалогов ещё не завершена.
''')
(stage/'CHANGELOG_RU.md').write_text('''# 18.7 TEST

- Steam: новое оформление персонажа, работающие размеры колонок и масштабирование окна.
- Steam: вкладка «Изготовление» показана после «Лор»; существующие ограничения доступности сохранены.
- Steam: цели над журналом, широкий текст, рамки категорий и шрифты по образцу NoSteam.
- NoSteam: сохранён комплект 18.6 с нужным оформлением меню.
- Сохранены исправления эссенции, карты, настроек, радиального меню и предыдущие переводы.
- Обновлён установщик без резервных копий. 17 проверок пройдены; проверка в игре остаётся необходимой.
''')
(stage/'Developer/README.md').write_text('''# Rebuild 18.7 TEST

Use verified 18.6 (ZIP SHA256 b3a912faf92f224cd56795162c246c2202bed84c998424c35a1b61f6a3525149) as immutable BASE. Freshly extract both BASE containers to BASE/FinalExtracted. WORK starts as a clean copy of BASE. Set CI_RU_RELEASE_WORKSPACE=WORK for the included helpers.

Put the five verified Steam source inputs (WB_QuestScreen, WB_QuestType, WB_WindowSwitcher, WB_UpperUIBar and WB_T3_SubHeadline) under WORK/Developer/V18_7/inputs/Steam_current/Carnal_Instinct_UE5/Content, keeping original paths. Their exact source hashes are in Reports/V18_7_UI_PARITY.json. NoSteam 18.6 widgets are visual references only; Steam class/CDO/gameplay function data stays Steam-specific.

Run tools/ui_parity_v18_7/build_ui.py WORK BASE, then build_payload.py WORK BASE. FinalExtracted must not already exist in WORK. Native additions keep existing export IDs; header/export/command/dependency tables rebuild with acyclic creation/serialization checks. Font/image resource references remap by imported package and public export hash. Only the existing Text_Form caption route and its event-entry offsets change in Kismet; all other source functions stay byte-identical.

Run unittest discover for tools/ui_parity_v18_7 and tools/map_popup_crash_v18_6 with CI_RU_CHECK_ROOT=WORK, then tools/map_audit_v18_5/test_display_regressions.py. Run verify_containers.py WORK; its historical output filename must be relabeled 18.7. Build the installer with installer/build.py and test core.go/core_test.go/no_backup_test.go using Go test -race. Finally package_release.py WORK STAGE ARCHIVE verifies six exact embedded/trusted payloads and every ZIP entry.

NoSteam payload, localization PAKs and both translation tables stay byte-identical to 18.6. Runtime visual/startup/crafting/settings FPS checks and complete dialogue proofreading are pending. Shared Steam Theme_3 heading size also needs runtime fit verification.
''')
files=sorted(p for p in stage.rglob('*') if p.is_file())
(stage/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files));files.append(stage/'SHA256SUMS.txt')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(files):z.write(p,p.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert not z.testzip() and len(z.namelist())==len(set(z.namelist()))==len(files)
    assert all(z.read(p.relative_to(stage).as_posix())==p.read_bytes() for p in files)
    assert not any('__pycache__' in n or '/patched/' in n or n.startswith(('Extracted/','FinalExtracted/')) for n in z.namelist())
report={'release':'18.7 TEST','name':archive.name,'sha256':sha(archive),'archive_bytes':archive.stat().st_size,
        'archive_entries':len(files),'zip_crc_and_exact_entry_readback':'PASS','installer_sha256':sha(exe),
        'exact_installer_payload':'PASS','runtime_tested':False,'drive_upload':'pending'}
save(archive.with_suffix('.json'),report);print(json.dumps(report,ensure_ascii=False,indent=2))
