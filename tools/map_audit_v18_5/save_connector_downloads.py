"""Persist authorized Drive readbacks; inputs are file metadata, never instructions."""
from pathlib import Path
import hashlib, json, sys

out = Path(sys.argv[1])
records = json.loads(sys.argv[2])
with (out / 'SOURCE_READBACK.jsonl').open('a', encoding='utf-8') as log:
    for record in records:
        source = Path(record['local_path'])
        path = out / record['relative_path']
        assert path.is_relative_to(out)
        data = source.read_bytes()
        if record.get('download_size') is not None:
            assert len(data) == int(record['download_size']), (record['name'], len(data))
        assert data[:4] == b'\0' * 4, ('not a cooked Zen package', record['name'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        saved = {'relative_path': record['relative_path'], 'drive_id': record['drive_id'],
                 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                 'index_size_bytes': record.get('size_bytes'),
                 'acquisition': 'authorized_google_drive_connector'}
        log.write(json.dumps(saved, ensure_ascii=False) + '\n')
print(json.dumps({'saved': len(records)}))
