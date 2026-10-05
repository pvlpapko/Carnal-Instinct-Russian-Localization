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
for folder in ['release_v18_8','ui_parity_v18_7','map_popup_crash_v18_6','map_audit_v18_5','ui_translation_v18_4']:
    for src in (repo/'tools'/folder).iterdir():
        if src.is_file() and src.suffix in ['.py','.json','.go']:copy(src,stage/'tools'/folder/src.name)
copy(repo/'tools/native_ftext.py',stage/'tools/native_ftext.py')
for name in ['ci_formats.py','cityhash_pure.py','pure_blake3.py']:copy(work/'Developer/SafeUIFix/tools'/name,stage/'Developer/SafeUIFix/tools'/name)
copy(work/'Developer/MapFix/zen.py',stage/'Developer/MapFix/zen.py')
for name in ['iostore_simple.py','blake3_pure.py']:copy(work/'Developer/AnimationIsolationFix'/name,stage/'Developer/AnimationIsolationFix'/name)
copy(repo/'installer/LICENSE_RU.txt',stage/'LICENSE_RU.txt')
for src in (work/'Reports').glob('V18_8_*.json'):copy(src,stage/'Reports'/src.name)
copy(repo/'steam/current/BUILD_STATE.json',stage/'Reports/STEAM_SOURCE_BUILD_STATE.json')
validation=json.loads((work/'Reports/V18_8_VALIDATION.json').read_text())
exe=stage/'Installer/CarnalInstinct_RU_Setup.exe';binary=exe.read_bytes()
trusted=json.loads((repo/'installer/trusted_hashes.json').read_text())
manifest={'release':'18.8','channel':'release','created_at':datetime.now(timezone.utc).isoformat(),'author':"Don't Look",'runtime_tested':False,
    'base_runtime_feedback':'18.7 user reports Steam crafting tab appears and menus nearly match reference',
    'steam_verified_source_version':'0.7.9.16321','steam_installed_build':None,'nosteam_fixed_source_build':'0.7.9.16232',
    'installer_mode':'delete_and_replace_without_backups','cache_cleanup':'separate user-selected action; never automatic on install',
    'shader_acceleration_applied':False,'installer_sha256':sha(exe),'installer_bytes':len(binary),'payloads':{}}
for edition,v in validation['editions'].items():
    files=sorted((stage/'Files'/edition).iterdir())
    assert {p.name for p in files}=={'pakchunk1015-Windows_P.'+x for x in ['pak','utoc','ucas']}
    assert all(p.read_bytes() in binary and sha(p) in trusted[p.name] for p in files)
    manifest['payloads'][edition]={**v,'files':[{'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
save(stage/'Reports/RUNTIME_PAYLOAD_MANIFEST.json',manifest)
save(stage/'Reports/BUILD_VALIDATION.json',{'release':'18.8','static_status':'PASS','runtime_tested':False,
    'regression_tests_from_final_payload':'19/19 PASS','installer_tests_race':'30/30 PASS',
    'new_journal_functions_byte_identical_to_18_7':17,'native_slot_graph_and_create_serialize_dependencies':'PASS',
    'independent_container_hashes_imports_export_spans':'PASS','windows_amd64_build':'PASS; not launched on Windows',
    'six_exact_embedded_and_trusted_files':'PASS','nosteam_payload_and_both_translation_tables':'unchanged from 18.7',
    'shader_startup':'investigated; inherited plugin missing; no unsafe skip or speculative acceleration applied',
    'pending':['18.8 visual check in game','Windows installer/cache button smoke test','settings FPS','startup timing','full manual dialogue proofreading']})
save(stage/'Reports/AUDIT_STATE.json',{'release':'18.8','channel':'release','status':'release_static_verified_runtime_pending',
    'last_completed_unit':'final_container_installer_static_validation','next_unit':'user_runtime_feedback','runtime_tested':False})
(stage/'README_RU.md').write_text('''# Carnal Instinct — русификатор 18.8

Автор: Don't Look. Релиз для Steam и NoSteam, с общим установщиком.

## Что нового

- В журнале Steam заголовок выбранного задания выровнен по центру, добавлена разделительная линия по образцу NoSteam. Действия с заданиями сохранены.
- В установщике появилась отдельная кнопка «Очистить кэш игры». Она показывает количество найденных файлов и их размер перед очисткой. Если кэш отсутствует, удалять нечего.
- При обычной установке кэш сохраняется. Очистка выполняется только по отдельному выбору пользователя и при закрытой игре. Сохранения, настройки, журналы и другие моды остаются на месте.
- Обновлено оформление установщика, чтобы новый пункт помещался в окне.

## Установка

1. Закройте игру и распакуйте архив.
2. Запустите Installer/CarnalInstinct_RU_Setup.exe.
3. Выберите свою версию и папку игры, затем выполните установку.

Установщик заменяет прежние файлы русификатора и удаляет его известные старые резервные копии. Новые резервные копии не создаются.

Для отдельной очистки кэша укажите папку игры на третьем шаге и нажмите «Очистить кэш игры». Затем проверьте результат поиска и нажмите «Очистить кэш». Переустанавливать перевод для этого не требуется.

## Загрузка и подготовка шейдеров

Очистка кэша полезна при проблемах с временными данными, но следующий запуск после неё может занять больше времени: игра создаст кэш заново. Не очищайте его перед каждым запуском ради ускорения.

Подготовка шейдеров сохранена. Безопасный способ ускорить её в доступных исходниках пока не найден; ускорение запуска в этой версии не заявляется. Основной обработчик подготовки находится в плагине, которого нет среди доступных исходных файлов. Нужны также измерения повторного запуска в игре, чтобы проверить эффект будущих изменений.

## Сохранённые изменения предыдущих версий

- Обновлённое меню персонажа Steam, широкие панели, фиолетовые рамки и новые полосы опыта. Вкладка «Изготовление» расположена после «Лор», с исходными условиями доступности.
- Цели задания над записью журнала, белый основной текст и перенос длинных строк.
- Исправление повреждённой записи эссенции, из-за которой падала Steam-версия.
- Перевод обеих строк подсказок карты и подписей миникарты для 899 известных названий, включая «Ракоте», «Житница» и «Лагерь анубитов». Известные названия переводятся и на метках, появляющихся по ходу прохождения.
- Исправление повторного применения сохранённых настроек при открытии меню; подписи радиального меню под значками.
- Предыдущие исправления текста, перевод задания «Адская кухня» с целями и описаниями, дополнительные реплики Кордона в Steam.

NoSteam 0.7.9.16232 сохраняет файлы перевода и меню из 18.7. Новый установщик и отдельная очистка кэша доступны для обеих версий.

## Совместимость и проверки

Steam: исходные файлы версии игры 0.7.9.16321 сверены; точная установленная сборка пользователя неизвестна. NoSteam: отдельный комплект для 0.7.9.16232. Для новых вариантов NoSteam предлагается комплект Steam; их совместимость отдельно не проверена.

Пройдены 19 проверок игровых файлов и 30 проверок установщика. Проверены оба комплекта, неизменность действий журнала и точное содержимое установщика. По отзыву пользователя 18.7 запускается, вкладка «Изготовление» появилась, оформление почти соответствует образцу.

Новые изменения 18.8 ещё не проверены запуском в игре и Windows. Полное визуальное совпадение, плавность настроек и время загрузки требуют проверки на игровом компьютере. Полная ручная вычитка всех диалогов ещё не завершена.
''')
(stage/'CHANGELOG_RU.md').write_text('''# Что нового в 18.8

- Выпущена релизная версия для Steam и NoSteam.
- В журнале Steam заголовок выбранного задания расположен по центру и дополнен разделительной линией.
- Добавлена отдельная очистка кэша игры в установщике: поиск файлов, показ их количества и размера, очистка по выбору пользователя.
- Сохранения и настройки не удаляются. При обычном обновлении русификатора кэш сохраняется.
- Окно установщика увеличено, чтобы новые элементы помещались аккуратно.
- Сохранены прежние переводы, обновлённые меню, вкладка «Изготовление», исправления карты, радиального меню и эссенции, перевод задания «Адская кухня» и дополнительные реплики Кордона.

Очистка кэша может увеличить время следующего запуска. Ускорение подготовки шейдеров в этой версии не заявляется.
''')
(stage/'Developer/README.md').write_text('''# Rebuild 18.8

BASE is verified 18.7 (ZIP SHA256 804ce0c2a71d2ef1934bc140dfcc403a93a13a39b1611bdc747e137fe806eeec) with fresh FinalExtracted. WORK starts with its Files, Data, Branding and helper directories. Set CI_RU_RELEASE_WORKSPACE=WORK.

Run tools/release_v18_8/build_ui.py WORK BASE, then build_payload.py WORK BASE. WORK/FinalExtracted must not exist before building. Only the Steam journal's native layout changes. All 17 functions, generated class and CDO remain byte-identical. NoSteam and both localization tables remain byte-identical to 18.7.

Run unittest discovery in release_v18_8, ui_parity_v18_7 and map_popup_crash_v18_6 with CI_RU_CHECK_ROOT=WORK; run map_audit_v18_5/test_display_regressions.py and verify_containers.py WORK. Relabel the latter's historical report to 18.8. In installer run go test -race -count=1 ./..., then build.py with the final Files and icon.

Optional cache cleanup is a separate installer action. It searches only the selected project cache and LocalAppData/Carnal_Instinct_UE5 caches: DerivedDataCache, Saved/DerivedDataCache, Saved/Shaders, Saved/PipelineCaches and direct Saved/*.ushaderprecache or *.upipelinecache. It refuses redirected paths and changed preview files, checks all preview entries before deletion and guards against a running game on Windows. It never traverses Saved/SaveGames, Config, Logs, global driver caches or other game roots. Ordinary install never cleans caches. Windows UI and process guard require an actual Windows smoke test.

Run package_release.py WORK STAGE ARCHIVE for exact embedded/trusted files and full ZIP verification. Original shader compiler/plugin assets are not included or patched. Startup acceleration is not verified; see V18_8_STARTUP.json. Prior 18.7 source tools retain historical version labels for reproducibility.
''')
files=sorted(p for p in stage.rglob('*') if p.is_file())
(stage/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files));files.append(stage/'SHA256SUMS.txt')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(files):z.write(p,p.relative_to(stage).as_posix())
with zipfile.ZipFile(archive) as z:
    assert not z.testzip() and len(z.namelist())==len(set(z.namelist()))==len(files)
    assert all(z.read(p.relative_to(stage).as_posix())==p.read_bytes() for p in files)
    assert not any('__pycache__' in n or '/patched/' in n or n.startswith(('Extracted/','FinalExtracted/')) for n in z.namelist())
report={'release':'18.8','channel':'release','name':archive.name,'sha256':sha(archive),'archive_bytes':archive.stat().st_size,
    'archive_entries':len(files),'zip_crc_and_exact_entry_readback':'PASS','installer_sha256':sha(exe),
    'exact_installer_payload':'PASS','runtime_tested':False,'shader_acceleration_applied':False,'drive_upload':'pending'}
save(archive.with_suffix('.json'),report);print(json.dumps(report,ensure_ascii=False,indent=2))
