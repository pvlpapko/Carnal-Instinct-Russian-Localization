"""Package a release with the exact verified payload and optional cache installer."""
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
for folder in ['ui_font_tracking_v18_9','release_v18_8','ui_parity_v18_7','map_popup_crash_v18_6','map_audit_v18_5','ui_translation_v18_4']:
    for src in (repo/'tools'/folder).iterdir():
        if src.is_file() and src.suffix in ['.py','.json','.go']:copy(src,stage/'tools'/folder/src.name)
copy(repo/'tools/native_ftext.py',stage/'tools/native_ftext.py')
for name in ['ci_formats.py','cityhash_pure.py','pure_blake3.py']:copy(work/'Developer/SafeUIFix/tools'/name,stage/'Developer/SafeUIFix/tools'/name)
copy(work/'Developer/MapFix/zen.py',stage/'Developer/MapFix/zen.py')
for name in ['iostore_simple.py','blake3_pure.py']:copy(work/'Developer/AnimationIsolationFix'/name,stage/'Developer/AnimationIsolationFix'/name)
copy(repo/'installer/LICENSE_RU.txt',stage/'LICENSE_RU.txt')
for src in (work/'Reports').glob('V18_9_*.json'):copy(src,stage/'Reports'/src.name)
copy(repo/'steam/current/BUILD_STATE.json',stage/'Reports/STEAM_SOURCE_BUILD_STATE.json')
validation=json.loads((work/'Reports/V18_9_VALIDATION.json').read_text())
exe=stage/'Installer/CarnalInstinct_RU_Setup.exe';binary=exe.read_bytes()
trusted=json.loads((repo/'installer/trusted_hashes.json').read_text())
manifest={'release':'18.9','channel':'release','created_at':datetime.now(timezone.utc).isoformat(),'author':"Don't Look",'runtime_tested':False,
    'base_runtime_feedback':'18.8 user screenshots show running Steam with centered journal title; settings headings and tracking clipping corrected natively in18.9',
    'steam_verified_source_version':'0.7.9.16321','steam_installed_build':None,'nosteam_fixed_source_build':'0.7.9.16232',
    'installer_mode':'delete_and_replace_without_backups','cache_cleanup':'separate user-selected action; never automatic on install',
    'shader_acceleration_applied':False,'installer_sha256':sha(exe),'installer_bytes':len(binary),'payloads':{}}
for edition,v in validation['editions'].items():
    files=sorted((stage/'Files'/edition).iterdir())
    assert {p.name for p in files}=={'pakchunk1015-Windows_P.'+x for x in ['pak','utoc','ucas']}
    assert all(p.read_bytes() in binary and sha(p) in trusted[p.name] for p in files)
    manifest['payloads'][edition]={**v,'files':[{'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
save(stage/'Reports/RUNTIME_PAYLOAD_MANIFEST.json',manifest)
save(stage/'Reports/BUILD_VALIDATION.json',{'release':'18.9','static_status':'PASS','runtime_tested':False,
    'regression_tests_from_final_payload':'23/23 PASS','installer_tests_race':'30/30 PASS',
    'all_changed_ui_functions_byte_identical_to_18_8':39,'native_slot_graph_and_create_serialize_dependencies':'PASS',
    'independent_container_hashes_imports_export_spans':'PASS','windows_amd64_build':'PASS; not launched on Windows',
    'six_exact_embedded_and_trusted_files':'PASS','nosteam_payload_and_both_translation_tables':'unchanged from 18.7',
    'shader_startup':'Plugin and Plugins reviewed; manifest points to absent Engine/Plugins/Marketplace/ShaderCompilationScreen; no shader skipping or speculative acceleration',
    'pending':['18.9 visual check in game','Windows installer/cache button smoke test','settings FPS','startup timing','full manual dialogue proofreading']})
save(stage/'Reports/AUDIT_STATE.json',{'release':'18.9','channel':'release','status':'release_static_verified_runtime_pending',
    'last_completed_unit':'final_container_installer_static_validation','next_unit':'user_runtime_feedback','runtime_tested':False})
(stage/'README_RU.md').write_text('''# Carnal Instinct — русификатор 18.9

Автор: Don't Look. Релиз для Steam и NoSteam, с общим установщиком.

## Что исправлено в Steam

- Уменьшены заголовки категорий во всех вкладках настроек, включая видео, графику, звук, управление, игру и настройки Lovense. Общему стилю возвращён исходный размер; перенос длинных строк сохранён.
- Уменьшен основной текст целей задания и записей журнала, а также их заголовки. Сохранены белый текст, переносы строк и расположение целей над журналом.
- Уменьшены значки выполнения целей и значок отслеживания задания. Значок отслеживания теперь расположен внутри карточки; убран отступ за её край и исправлена ширина карточки с учётом полей.
- Действия с заданиями, условия отслеживания и доступность кнопок сохранены.

## Установка

1. Закройте игру и распакуйте архив.
2. Запустите Installer/CarnalInstinct_RU_Setup.exe.
3. Выберите свою версию и папку игры, затем выполните установку.

Прежние файлы русификатора заменяются, его известные старые резервные копии удаляются. Новые резервные копии не создаются. При обычной установке кэш игры сохраняется.

Кнопка «Очистить кэш игры» на третьем шаге работает отдельно от установки: сначала показывает количество найденных файлов и их размер. Сохранения, настройки, журналы и другие моды сохраняются. После очистки следующий запуск может занять больше времени.

## Подготовка шейдеров

Проверены обе папки Plugin и Plugins на Диске и список плагинов игры. Нужный обработчик ShaderCompilationScreen относится к папке Engine/Plugins/Marketplace/ShaderCodcddcf8247c4V6. Его файлов нет среди доступных папок. Загруженные плагины DLSS, FSR, XeSS и Streamline решают другие задачи.

Подготовка шейдеров сохранена; ускорение запуска в этой версии не заявляется. Для продолжения этой работы нужны файлы указанного плагина и измерения повторного запуска в игре.

## Сохранённые изменения

- Обновлённое меню персонажа и вкладка «Изготовление» после «Лор».
- Широкий журнал, заголовок выбранного задания по центру с разделительной линией.
- Перевод обеих строк подсказок карты и миникарты для 899 известных названий, включая «Ракоте», «Житница» и «Лагерь анубитов». Известные названия переводятся и на метках, появляющихся по ходу прохождения.
- Исправление повреждённой записи эссенции, повторного применения настроек при открытии меню и расположения подписей радиального меню.
- Предыдущие исправления текста, перевод задания «Адская кухня» с целями и описаниями, дополнительные реплики Кордона в Steam.

NoSteam 0.7.9.16232 сохраняет игровые файлы и перевод из 18.8: новые замечания по размерам касались Steam. Общий установщик и отдельная очистка кэша доступны для обеих версий.

## Совместимость и проверки

Steam: исходные файлы версии игры 0.7.9.16321 сверены; точная установленная сборка пользователя неизвестна. NoSteam: отдельный комплект для 0.7.9.16232. Для новых вариантов NoSteam предлагается комплект Steam; их совместимость отдельно не проверена.

Пройдены 23 проверки игровых файлов и 30 проверок установщика. Проверены оба комплекта, размеры текста и отступы, неизменность 39 обработчиков изменённых меню и точное содержимое установщика.

Новые изменения 18.9 ещё не проверены запуском в игре и Windows. Внешний вид, плавность настроек и время загрузки требуют проверки на игровом компьютере. Полная ручная вычитка всех диалогов ещё не завершена.
''')
(stage/'CHANGELOG_RU.md').write_text('''# Что нового в 18.9

- Исправлен слишком крупный текст категорий во всех вкладках настроек Steam, включая Lovense.
- Уменьшен текст целей заданий, записей журнала и их заголовков.
- Уменьшены значки выполнения целей и отслеживания заданий; значок отслеживания перенесён внутрь карточки, чтобы его не обрезало.
- Сохранены прежние переводы и исправления, меню персонажа, вкладка «Изготовление» и отдельная очистка кэша в установщике.
- Файлы NoSteam сохранены из предыдущего релиза.

Ускорение подготовки шейдеров в этой версии не заявляется: нужного плагина ShaderCompilationScreen из Engine/Plugins/Marketplace пока нет среди доступных файлов.
''')
(stage/'Developer/README.md').write_text('''# Rebuild 18.9

BASE is verified 18.8 (ZIP SHA256 75c7f905d640a4670803daa1cc51b352d6c609f51ef6e2663f1dd09d9d1158e8) with fresh FinalExtracted. WORK starts with Files, Data, Branding and helper directories. Set CI_RU_RELEASE_WORKSPACE=WORK.

Run tools/ui_font_tracking_v18_9/build_ui.py WORK BASE, then build_payload.py WORK BASE. WORK/FinalExtracted must not exist before building. Five Steam widgets change only native UMG font/style/geometry records. All39 functions and generated classes/CDOs remain byte-identical. NoSteam and both localization tables remain byte-identical to18.8.

Run unittest discovery in ui_font_tracking_v18_9, release_v18_8, ui_parity_v18_7 and map_popup_crash_v18_6 with CI_RU_CHECK_ROOT=WORK; run map_audit_v18_5/test_display_regressions.py and verify_containers.py WORK. Relabel the latter's historical report to18.9. In installer run go test -race -count=1 ./..., then build.py with final Files and icon. Finally use this folder's package_release.py WORK STAGE ARCHIVE to verify exact embedded/trusted payloads and every ZIP entry.

Settings shared heading32→16, quest body20→16, section labels22→18, objective status size32→24. Tracking checkbox64→28 across states, render scale1.1→1; overlay right margin-16→10; card530 + outer margins20 fits550 list. No text identities, resource IDs, gameplay/input/progression scripts or binding records changed.

The inherited shader compiler belongs to Engine/Plugins/Marketplace/ShaderCodcddcf8247c4V6. Both uploaded project-plugin folders and the207-entry manifest were inspected; the required plugin is not available. Shader preparation is not patched or skipped. Optional cache cleanup remains a separate user-selected installer action, preserving saves, Config, Logs, other mods and shared driver caches. Ordinary install retains caches. Prior source tools keep historical release labels for reproducibility.
''')
files=sorted(p for p in stage.rglob('*') if p.is_file())
(stage/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files));files.append(stage/'SHA256SUMS.txt')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(files):z.write(p,p.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert not z.testzip() and len(z.namelist())==len(set(z.namelist()))==len(files)
    assert all(z.read(p.relative_to(stage).as_posix())==p.read_bytes() for p in files)
    assert not any('__pycache__' in n or '/patched/' in n or n.startswith(('Extracted/','FinalExtracted/')) for n in z.namelist())
report={'release':'18.9','channel':'release','name':archive.name,'sha256':sha(archive),'archive_bytes':archive.stat().st_size,
    'archive_entries':len(files),'zip_crc_and_exact_entry_readback':'PASS','installer_sha256':sha(exe),
    'exact_installer_payload':'PASS','runtime_tested':False,'shader_acceleration_applied':False,'drive_upload':'pending'}
save(archive.with_suffix('.json'),report);print(json.dumps(report,ensure_ascii=False,indent=2))
