"""Isolate the eight v18.4 Steam resource changes from LOCRES and v18.3."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys, zipfile
from display_tools import cf, sha

ROOT, BASE, FAILED, OUT, GO = map(Path, sys.argv[1:6])
repo = Path(__file__).resolve().parents[2]
assert not OUT.exists(), 'Use a fresh diagnostic directory'
OUT.mkdir(parents=True)
names = ['pakchunk1015-Windows_P.' + e for e in ('pak', 'utoc', 'ucas')]
def load(root):
    toc = cf.Toc(root / 'Files/Steam_current' / names[1])
    return {p: toc.read_chunk(i) for p, i in toc.files}
a, b = load(BASE), load(FAILED)
changes = [p for p in b if p not in a or a[p] != b[p]]
assert len(changes) == 8 and not a.keys() - b.keys()
order = ['WB_QuestObjectiveName', 'WB_QuestObjectiveDescription', 'WB_QuestName',
         'WB_Stats_Full', 'WB_Stats_Main_Slot', 'WB_T3_NSM_Button', 'WB_T3_Lovense', 'Essence_Tier_1_Small']
changes = [next(p for p in changes if Path(p).stem == n) for n in order]
manifest = {'purpose': 'v18.4 startup resource isolation; not a crash fix', 'runtime_tested': False,
            'verified_source_version': '0.7.9.16321', 'installed_steam_build': None, 'stages': []}
known = json.loads((repo / 'installer/trusted_hashes.json').read_text())
files = dict(a)
for i in range(10):
    if i >= 2: files[changes[i - 2]] = b[changes[i - 2]]
    folder = f'{i:02d}'
    dest = OUT / 'Payloads' / folder
    dest.mkdir(parents=True)
    shutil.copy2((BASE if i == 0 else FAILED) / 'Files/Steam_current' / names[0], dest / names[0])
    if i <= 1:
        for n in names[1:]: shutil.copy2(BASE / 'Files/Steam_current' / n, dest / n)
    else:
        original = cf.build_directory
        cf.build_directory = lambda pairs, mount='../../../': original([(idx, p) for p, idx in pairs], mount)
        try: cf.build_container(list(files.items()), dest / names[1])
        finally: cf.build_directory = original
    toc = cf.Toc(dest / names[1]); assert not toc.verify_meta()
    assert {p: toc.read_chunk(idx) for p, idx in toc.files} == files
    if i == 9:
        assert files == b
        assert all((dest / n).read_bytes() == (FAILED / 'Files/Steam_current' / n).read_bytes() for n in names), 'final stage must reproduce failed release exactly'
    stage = {'folder': folder, 'label': '18.3 без изменений' if i == 0 else ('18.3 + только перевод 18.4' if i == 1 else '+ ' + order[i - 2]),
             'added_or_changed_asset': changes[i - 2] if i >= 2 else None, 'packages': len(files),
             'files': [{'name': n, 'sha256': sha((dest / n).read_bytes())} for n in names]}
    manifest['stages'].append(stage)
    for f in stage['files']:
        values = known.setdefault(f['name'], [])
        if f['sha256'] not in values: values.append(f['sha256'])
(OUT / 'PROBE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
(OUT / 'trusted_hashes.json').write_text(json.dumps(known, indent=2) + '\n')
build = OUT / 'Source'; build.mkdir()
shutil.copy2(repo / 'installer/core.go', build / 'core.go')
shutil.copy2(Path(__file__).with_name('probe_main.go'), build / 'probe_main.go')
shutil.copy2(Path(__file__).with_name('probe_main_test.go'), build / 'probe_main_test.go')
shutil.copy2(repo / 'installer/LICENSE_RU.txt', OUT / 'LICENSE_RU.txt')
env = os.environ.copy(); env.update(GOTOOLCHAIN='local', GOPROXY='off', CGO_ENABLED='0')
env['CI_RU_PROBE_ROOT'] = str(OUT)
subprocess.run([str(GO), 'test', '-buildvcs=false', '-count=1', 'core.go', 'probe_main.go', 'probe_main_test.go'], cwd=build, env=env, check=True)
subprocess.run([str(GO), 'build', '-buildvcs=false', '-trimpath', '-o', str(OUT / 'probe-host-check'), 'core.go', 'probe_main.go'], cwd=build, env=env, check=True)
subprocess.run([str(OUT / 'probe-host-check'), '--verify'], check=True)
(OUT / 'probe-host-check').unlink()
env.update(GOOS='windows', GOARCH='amd64')
subprocess.run([str(GO), 'build', '-buildvcs=false', '-trimpath', '-ldflags=-s -w', '-o', str(OUT / 'Steam_Startup_Probe.exe'), 'core.go', 'probe_main.go'], cwd=build, env=env, check=True)
text = '''# Диагностика краша Steam 18.4

Это отдельный набор для поиска причины, не исправление краша и не полный перевод 18.5. Только для Steam. Набор 0 точно воспроизводит 18.3, набор 9 — файлы Steam 18.4, на которых сообщён краш. Между ними по одному добавлены изменения, указанные в PROBE_MANIFEST.json. NoSteam не устанавливайте этим инструментом.

1. Распакуйте весь архив, закройте игру. Запустите Steam_Startup_Probe.exe, выберите 0 и укажите папку игры Steam. Проверьте появление главного меню.
2. Если 0 запускается, проверьте 9. Если 9 тоже запускается, сообщите оба результата: проблема 18.4 не воспроизведена на этой установке.
3. Если 0 запускается, а 9 падает, проверьте 5. При краше 5 проверьте 2, затем середину оставшегося диапазона; если 5 запускается — проверьте 7, затем 6 или 8. Так определяется соседняя пара «запускается / падает» за несколько запусков. Сообщите номера этой пары, точную версию Steam и свежий CrashContext.runtime-xml.
4. Если 0 падает, сравнение изменений 18.4 пока невозможно: сообщите этот результат и версию игры.

После каждого теста полностью закройте игру. Затем обычным установщиком поставьте выбранную рабочую версию перевода или удалите русификатор. Программа заменяет только три файла этого русификатора, не создаёт бэкапы и использует проверенный механизм установщика с проверкой контрольных сумм. Сохранения не изменяет. Не проверяйте прохождение на промежуточных наборах: их задача — запуск до главного меню.

10 наборов прошли чтение контейнеров и проверку 30 SHA256. Консольный установщик собран для Windows amd64, проверка файлов выполнялась на Linux; запуск в Windows и игре пока не проверен. Исходный код включён.
'''
(OUT / 'README_RU.md').write_text(text)
archive = Path(str(OUT) + '.zip')
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file(): z.write(p, p.relative_to(OUT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert not z.testzip()
    for p in OUT.rglob('*'):
        if p.is_file(): assert z.read(p.relative_to(OUT).as_posix()) == p.read_bytes()
report = {'name': archive.name, 'sha256': sha(archive.read_bytes()), 'archive_bytes': archive.stat().st_size,
          'stages': 10, 'runtime_tested': False, 'last_stage_exact_failed_release_readback': 'PASS',
          'all_stage_container_and_file_readback': 'PASS', 'host_verify_mode': 'PASS', 'zip_crc_and_entry_readback': 'PASS'}
(ROOT / 'Reports/V18_5_STARTUP_PROBE.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
