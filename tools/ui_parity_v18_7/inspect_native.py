"""Inspect full native UMG properties and hierarchy using the verified UE5.5 schema."""
from pathlib import Path
import json, sys, hashlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'map_audit_v18_5'))
from display_tools import ui, cf, k, find_script, expr_name

META = Path('/workspace/project-context/carnal-instinct/legacy-reference/CarnalInstinct_0.7.9.16232.usm')
metadata = json.loads(META.read_text())['objects']
ui.NATIVE['/Script/CoreUObject.Box2D'] = '4dB'
ui.NATIVE['/Script/SlateCore.DeprecateSlateVector2D'] = '2f'
ui.NATIVE['/Script/CoreUObject.Vector4f'] = '4f'

def clean(field):
    value = {k: field[k] for k in ('name', 'array_dim', 'type', 'struct', 'enum') if k in field}
    for key in ('inner', 'key', 'value'):
        if key in field:
            value[key] = clean(field[key])
            value[key].pop('name', None)
    return value

def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items() if k != 'array_dim'}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value

for key, obj in metadata.items():
    if not key.startswith('/Script/') or obj['type'] not in ('Class', 'ScriptStruct'):
        continue
    schema = {'super': obj.get('super_struct'), 'properties': [clean(f) for f in obj.get('properties', [])]}
    if key in ui.SCHEMA:
        old = ui.SCHEMA[key]
        assert old['super'] == schema['super']
        assert semantic({'super': old['super'], 'properties': [clean(f) for f in old['properties']]}) == semantic(schema), key
    ui.SCHEMA[key] = schema
    if key.startswith('/Script/UMG.') and obj['type'] == 'Class':
        path = key.replace('.', '/')
        ident = (cf.CityHash64(path.lower().encode('utf-16-le')) & ((1 << 62) - 1)) | (1 << 62)
        ui.CLASS[ident] = key.split('.')[-1]

def props(package, export):
    cls = ui.CLASS[export['cls']]
    raw = package['bytes'][export['start']:export['end']]
    values, end = ui.obj(raw, 0, '/Script/UMG.' + cls, package['names'])
    assert raw[end:] == b'\0' * 4, (export['name'], cls, raw[end:].hex())
    return values

def describe(path):
    p = ui.zen.package(path)
    result = {'path': str(path), 'sha256': hashlib.sha256(p['bytes']).hexdigest(), 'native': [], 'errors': []}
    for e in p['exports']:
        if e['cls'] not in ui.CLASS:
            continue
        cls = '/Script/UMG.' + ui.CLASS[e['cls']]
        ancestors = []
        while cls:
            ancestors.append(cls)
            cls = ui.SCHEMA[cls]['super']
        if not any(x in ancestors for x in ('/Script/UMG.Widget', '/Script/UMG.PanelSlot', '/Script/UMG.WidgetTree')):
            continue
        try:
            values = props(p, e)
            result['native'].append({'index': e['index'], 'name': e['name'], 'class': ui.CLASS[e['cls']],
                                     'outer': e['outer'], 'values': values})
        except Exception as ex:
            result['errors'].append({'index': e['index'], 'name': e['name'], 'class': ui.CLASS[e['cls']], 'error': str(ex)})
    return result

if __name__ == '__main__':
    path, output = map(Path, sys.argv[1:3])
    result = describe(path)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'path': str(path), 'native': len(result['native']), 'errors_count': len(result['errors']), 'errors': result['errors'][:4]}, ensure_ascii=False))
